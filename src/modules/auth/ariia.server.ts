/**
 * Cliente OAuth 2.1 + PKCE do Ariia (Identity Provider).
 * Server-only: faz troca de código, valida id_token via JWKS e renova tokens.
 */
import { createRemoteJWKSet, jwtVerify, type JWTPayload } from "jose";

import { ARIIA_AUTH_BASE_URL, ARIIA_CLIENT_ID, ARIIA_SCOPES } from "./config";

interface Discovery {
  issuer: string;
  authorization_endpoint: string;
  token_endpoint: string;
  jwks_uri: string;
  userinfo_endpoint?: string;
  end_session_endpoint?: string;
}

let discoveryCache: Discovery | undefined;
let jwksCache: ReturnType<typeof createRemoteJWKSet> | undefined;

/** O Ariia é um projeto Supabase; o gateway pode exigir o header `apikey`. */
function ariiaGatewayHeaders(): Record<string, string> {
  const anonKey = process.env["ARIIA_ANON_KEY"];
  return anonKey ? { apikey: anonKey } : {};
}

export async function getDiscovery(): Promise<Discovery> {
  if (discoveryCache) return discoveryCache;

  const url = `${ARIIA_AUTH_BASE_URL}/.well-known/openid-configuration`;
  const response = await fetch(url, { headers: ariiaGatewayHeaders() });

  if (!response.ok) {
    // Fallback para os endpoints padrão do Supabase Auth OAuth Server.
    discoveryCache = {
      issuer: ARIIA_AUTH_BASE_URL,
      authorization_endpoint: `${ARIIA_AUTH_BASE_URL}/oauth/authorize`,
      token_endpoint: `${ARIIA_AUTH_BASE_URL}/oauth/token`,
      jwks_uri: `${ARIIA_AUTH_BASE_URL}/.well-known/jwks.json`,
    };
    return discoveryCache;
  }

  discoveryCache = (await response.json()) as Discovery;
  return discoveryCache;
}

async function getJwks() {
  if (!jwksCache) {
    const discovery = await getDiscovery();
    jwksCache = createRemoteJWKSet(new URL(discovery.jwks_uri));
  }
  return jwksCache;
}

export async function buildAuthorizationUrl(params: {
  redirectUri: string;
  state: string;
  codeChallenge: string;
  nonce: string;
}): Promise<string> {
  const discovery = await getDiscovery();
  const url = new URL(discovery.authorization_endpoint);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", ARIIA_CLIENT_ID);
  url.searchParams.set("redirect_uri", params.redirectUri);
  url.searchParams.set("scope", ARIIA_SCOPES);
  url.searchParams.set("state", params.state);
  url.searchParams.set("nonce", params.nonce);
  url.searchParams.set("code_challenge", params.codeChallenge);
  url.searchParams.set("code_challenge_method", "S256");
  return url.toString();
}

export interface AriiaTokenSet {
  access_token: string;
  refresh_token?: string;
  id_token?: string;
  token_type?: string;
  expires_in?: number;
  scope?: string;
}

async function postToken(body: URLSearchParams): Promise<AriiaTokenSet> {
  const discovery = await getDiscovery();
  const response = await fetch(discovery.token_endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
      ...ariiaGatewayHeaders(),
    },
    body,
  });

  const text = await response.text();
  if (!response.ok) {
    throw new Error(
      `Falha na troca de token com o Ariia (${response.status}): ${text.slice(0, 300)}`,
    );
  }

  return JSON.parse(text) as AriiaTokenSet;
}

export async function exchangeAuthorizationCode(params: {
  code: string;
  redirectUri: string;
  codeVerifier: string;
}): Promise<AriiaTokenSet> {
  return postToken(
    new URLSearchParams({
      grant_type: "authorization_code",
      code: params.code,
      redirect_uri: params.redirectUri,
      client_id: ARIIA_CLIENT_ID,
      code_verifier: params.codeVerifier,
    }),
  );
}

export async function refreshAriiaTokens(refreshToken: string): Promise<AriiaTokenSet> {
  return postToken(
    new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: refreshToken,
      client_id: ARIIA_CLIENT_ID,
    }),
  );
}

export interface AriiaIdentity {
  ariiaUserId: string;
  email: string;
  nome: string | null;
  avatarUrl: string | null;
  claims: JWTPayload;
}

function pickString(source: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.trim().length > 0) return value.trim();
  }
  return null;
}

function toIdentity(claims: Record<string, unknown>): AriiaIdentity {
  const sub = pickString(claims, ["sub"]);
  const email = pickString(claims, ["email"]);
  if (!sub) throw new Error("Identidade do Ariia sem `sub`.");
  if (!email) throw new Error("Identidade do Ariia sem e-mail — escopo `email` é obrigatório.");

  const metadata =
    typeof claims["user_metadata"] === "object" && claims["user_metadata"] !== null
      ? (claims["user_metadata"] as Record<string, unknown>)
      : {};

  return {
    ariiaUserId: sub,
    email: email.toLowerCase(),
    nome:
      pickString(claims, ["name", "full_name", "preferred_username"]) ??
      pickString(metadata, ["name", "full_name"]),
    avatarUrl:
      pickString(claims, ["picture", "avatar_url"]) ??
      pickString(metadata, ["avatar_url", "picture"]),
    claims: claims as JWTPayload,
  };
}

/** Valida assinatura, issuer, audience e nonce do id_token emitido pelo Ariia. */
export async function verifyIdToken(idToken: string, nonce: string): Promise<AriiaIdentity> {
  const discovery = await getDiscovery();
  const jwks = await getJwks();

  const { payload } = await jwtVerify(idToken, jwks, {
    issuer: discovery.issuer,
    audience: ARIIA_CLIENT_ID,
    clockTolerance: 60,
  });

  if (typeof payload["nonce"] === "string" && payload["nonce"] !== nonce) {
    throw new Error("Nonce do id_token não corresponde à requisição de login.");
  }

  return toIdentity(payload as Record<string, unknown>);
}

/** Fallback quando o Ariia não devolve id_token: consulta o userinfo com o access token. */
export async function fetchUserInfo(accessToken: string): Promise<AriiaIdentity> {
  const discovery = await getDiscovery();
  const endpoint = discovery.userinfo_endpoint ?? `${ARIIA_AUTH_BASE_URL}/user`;
  const response = await fetch(endpoint, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: "application/json",
      ...ariiaGatewayHeaders(),
    },
  });

  if (!response.ok) {
    throw new Error(`Não foi possível obter a identidade no Ariia (${response.status}).`);
  }

  return toIdentity((await response.json()) as Record<string, unknown>);
}

/** Resolve a identidade preferindo o id_token e caindo para userinfo. */
export async function resolveIdentity(
  tokens: AriiaTokenSet,
  nonce: string,
): Promise<AriiaIdentity> {
  if (tokens.id_token) {
    try {
      return await verifyIdToken(tokens.id_token, nonce);
    } catch (error) {
      console.error("[Ariia] id_token inválido, tentando userinfo:", error);
    }
  }
  return fetchUserInfo(tokens.access_token);
}