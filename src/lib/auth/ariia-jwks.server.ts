/**
 * Verificação do id_token do Ariia contra o JWKS do IdP.
 * Server-only.
 */
import { createRemoteJWKSet, jwtVerify, decodeJwt, type JWTPayload } from "jose";

import { getAriiaConfig } from "./ariia-config.server";
import { getDiscovery } from "./ariia-oauth.server";

export type AriiaIdentity = {
  sub: string;
  email: string;
  emailVerified: boolean;
  name: string | null;
  picture: string | null;
};

let jwksCache: { uri: string; keySet: ReturnType<typeof createRemoteJWKSet> } | undefined;

function getKeySet(jwksUri: string) {
  if (!jwksCache || jwksCache.uri !== jwksUri) {
    jwksCache = { uri: jwksUri, keySet: createRemoteJWKSet(new URL(jwksUri)) };
  }
  return jwksCache.keySet;
}

function toIdentity(payload: JWTPayload): AriiaIdentity {
  const sub = typeof payload.sub === "string" ? payload.sub : "";
  const email = typeof payload['email'] === "string" ? payload['email'] : "";

  if (!sub) throw new Error("id_token do Ariia sem `sub`.");
  if (!email) throw new Error("id_token do Ariia sem `email`.");

  const rawName = payload['name'] ?? payload['full_name'] ?? payload['preferred_username'];
  const rawPicture = payload['picture'] ?? payload['avatar_url'];

  return {
    sub,
    email: email.toLowerCase(),
    emailVerified: payload['email_verified'] === true,
    name: typeof rawName === "string" && rawName.length > 0 ? rawName : null,
    picture: typeof rawPicture === "string" && rawPicture.length > 0 ? rawPicture : null,
  };
}

/** Valida assinatura, issuer, audience, expiração e nonce. */
export async function verifyAriiaIdToken(input: {
  idToken: string;
  expectedNonce: string;
}): Promise<AriiaIdentity> {
  const config = getAriiaConfig();
  const discovery = await getDiscovery(config);

  const { payload } = await jwtVerify(input.idToken, getKeySet(discovery.jwks_uri), {
    issuer: discovery.issuer,
    audience: config.clientId,
    clockTolerance: 60,
  });

  if (typeof payload['nonce'] === "string" && payload['nonce'] !== input.expectedNonce) {
    throw new Error("Nonce do id_token não corresponde ao da requisição.");
  }

  return toIdentity(payload);
}

/**
 * Fallback para quando o Ariia não devolve id_token: consulta o userinfo
 * com o access token e valida a identidade retornada.
 */
export async function fetchAriiaUserInfo(accessToken: string): Promise<AriiaIdentity> {
  const discovery = await getDiscovery();
  const endpoint = discovery.userinfo_endpoint ?? `${discovery.issuer}/user`;

  const response = await fetch(endpoint, {
    headers: { authorization: `Bearer ${accessToken}`, accept: "application/json" },
  });

  if (!response.ok) {
    const body = await response.text();
    console.error(`[Ariia] userinfo ${response.status}: ${body}`);
    throw new Error(`Não foi possível obter a identidade no Ariia (${response.status}).`);
  }

  return toIdentity((await response.json()) as JWTPayload);
}

/** Lê o `exp` de um token sem validar. Usado só para agendar refresh. */
export function readTokenExpiry(token: string): number | null {
  try {
    const payload = decodeJwt(token);
    return typeof payload.exp === "number" ? payload.exp : null;
  } catch {
    return null;
  }
}