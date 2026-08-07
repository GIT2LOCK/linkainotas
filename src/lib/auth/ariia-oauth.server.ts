/**
 * Cliente OAuth 2.1 + PKCE do Ariia.
 *
 * Server-only. Usa apenas Web Crypto (runtime Cloudflare Workers).
 */
import { getAriiaConfig, ARIIA_SCOPES, type AriiaConfig } from "./ariia-config.server";

export type AriiaDiscovery = {
  issuer: string;
  authorization_endpoint: string;
  token_endpoint: string;
  jwks_uri: string;
  revocation_endpoint?: string;
  userinfo_endpoint?: string;
  end_session_endpoint?: string;
};

export type AriiaTokenSet = {
  access_token: string;
  refresh_token?: string;
  id_token?: string;
  token_type: string;
  expires_in?: number;
  scope?: string;
};

let discoveryCache: { value: AriiaDiscovery; issuer: string; fetchedAt: number } | undefined;
const DISCOVERY_TTL_MS = 10 * 60 * 1000;

function base64UrlEncode(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function randomUrlSafeToken(byteLength = 32): string {
  return base64UrlEncode(crypto.getRandomValues(new Uint8Array(byteLength)));
}

export type PkcePair = { verifier: string; challenge: string };

export async function createPkcePair(): Promise<PkcePair> {
  const verifier = randomUrlSafeToken(32);
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return { verifier, challenge: base64UrlEncode(new Uint8Array(digest)) };
}

/** Fallback para os caminhos padrão do OAuth server do Supabase. */
function conventionalDiscovery(issuer: string): AriiaDiscovery {
  return {
    issuer,
    authorization_endpoint: `${issuer}/oauth/authorize`,
    token_endpoint: `${issuer}/oauth/token`,
    jwks_uri: `${issuer}/.well-known/jwks.json`,
  };
}

export async function getDiscovery(config?: AriiaConfig): Promise<AriiaDiscovery> {
  const { issuerUrl } = config ?? getAriiaConfig();

  if (
    discoveryCache &&
    discoveryCache.issuer === issuerUrl &&
    Date.now() - discoveryCache.fetchedAt < DISCOVERY_TTL_MS
  ) {
    return discoveryCache.value;
  }

  const candidates = [
    `${issuerUrl}/.well-known/openid-configuration`,
    `${issuerUrl}/.well-known/oauth-authorization-server`,
  ];

  for (const url of candidates) {
    try {
      const response = await fetch(url, { headers: { accept: "application/json" } });
      if (!response.ok) continue;
      const document = (await response.json()) as Partial<AriiaDiscovery>;
      if (!document.authorization_endpoint || !document.token_endpoint) continue;
      const value: AriiaDiscovery = {
        issuer: document.issuer ?? issuerUrl,
        authorization_endpoint: document.authorization_endpoint,
        token_endpoint: document.token_endpoint,
        jwks_uri: document.jwks_uri ?? `${issuerUrl}/.well-known/jwks.json`,
        ...(document.revocation_endpoint ? { revocation_endpoint: document.revocation_endpoint } : {}),
        ...(document.userinfo_endpoint ? { userinfo_endpoint: document.userinfo_endpoint } : {}),
        ...(document.end_session_endpoint ? { end_session_endpoint: document.end_session_endpoint } : {}),
      };
      discoveryCache = { value, issuer: issuerUrl, fetchedAt: Date.now() };
      return value;
    } catch (error) {
      console.error(`[Ariia] Falha ao ler discovery em ${url}:`, error);
    }
  }

  const fallback = conventionalDiscovery(issuerUrl);
  discoveryCache = { value: fallback, issuer: issuerUrl, fetchedAt: Date.now() };
  return fallback;
}

export async function buildAuthorizeUrl(input: {
  state: string;
  nonce: string;
  codeChallenge: string;
  redirectUri?: string;
}): Promise<string> {
  const config = getAriiaConfig();
  const discovery = await getDiscovery(config);

  const url = new URL(discovery.authorization_endpoint);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", config.clientId);
  url.searchParams.set("redirect_uri", input.redirectUri ?? config.redirectUri);
  url.searchParams.set("scope", ARIIA_SCOPES);
  url.searchParams.set("state", input.state);
  url.searchParams.set("nonce", input.nonce);
  url.searchParams.set("code_challenge", input.codeChallenge);
  url.searchParams.set("code_challenge_method", "S256");
  return url.toString();
}

async function postToken(body: URLSearchParams): Promise<AriiaTokenSet> {
  const discovery = await getDiscovery();
  const response = await fetch(discovery.token_endpoint, {
    method: "POST",
    headers: {
      "content-type": "application/x-www-form-urlencoded",
      accept: "application/json",
    },
    body,
  });

  const text = await response.text();
  if (!response.ok) {
    console.error(`[Ariia] token endpoint ${response.status}: ${text}`);
    throw new Error(`Falha na troca de tokens com o Ariia (${response.status}).`);
  }

  try {
    return JSON.parse(text) as AriiaTokenSet;
  } catch {
    throw new Error("Resposta inválida do token endpoint do Ariia.");
  }
}

export async function exchangeAuthorizationCode(input: {
  code: string;
  codeVerifier: string;
  redirectUri?: string;
}): Promise<AriiaTokenSet> {
  const config = getAriiaConfig();
  return postToken(
    new URLSearchParams({
      grant_type: "authorization_code",
      code: input.code,
      redirect_uri: input.redirectUri ?? config.redirectUri,
      client_id: config.clientId,
      code_verifier: input.codeVerifier,
    }),
  );
}

export async function refreshAriiaTokens(refreshToken: string): Promise<AriiaTokenSet> {
  const config = getAriiaConfig();
  return postToken(
    new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: refreshToken,
      client_id: config.clientId,
    }),
  );
}

export async function revokeAriiaToken(token: string): Promise<void> {
  const config = getAriiaConfig();
  const discovery = await getDiscovery(config);
  if (!discovery.revocation_endpoint) return;

  try {
    await fetch(discovery.revocation_endpoint, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ token, client_id: config.clientId }),
    });
  } catch (error) {
    console.error("[Ariia] Falha ao revogar token:", error);
  }
}