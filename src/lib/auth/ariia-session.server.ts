/**
 * Sessão A — identidade do Ariia.
 *
 * Cookie httpOnly cifrado, exclusivo do servidor. É a fonte de verdade:
 * a sessão Supabase do Linkai só sobrevive enquanto esta for válida.
 */
import { useSession } from "@tanstack/react-start/server";

import { getSessionSecret } from "./ariia-config.server";

export type AriiaSessionData = {
  ariiaSub: string;
  email: string;
  name: string | null;
  picture: string | null;
  refreshToken: string | null;
  accessTokenExpiresAt: number | null;
  authUserId: string;
  issuedAt: number;
};

const MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

const cookieOptions = {
  httpOnly: true,
  secure: true,
  sameSite: "lax" as const,
  path: "/",
};

function sessionConfig() {
  return {
    password: getSessionSecret(),
    name: "linkai_ariia",
    maxAge: MAX_AGE_SECONDS,
    cookie: cookieOptions,
  };
}

export async function readAriiaSession(): Promise<AriiaSessionData | null> {
  const session = await useSession<AriiaSessionData>(sessionConfig());
  const data = session.data;
  if (!data || !data.ariiaSub || !data.authUserId) return null;
  return data as AriiaSessionData;
}

export async function writeAriiaSession(data: AriiaSessionData): Promise<void> {
  const session = await useSession<AriiaSessionData>(sessionConfig());
  await session.update(data);
}

export async function clearAriiaSession(): Promise<void> {
  const session = await useSession<AriiaSessionData>(sessionConfig());
  await session.clear();
}

/** Estado efêmero do fluxo OAuth: state, PKCE verifier, nonce e destino. */
export type OAuthFlowData = {
  state: string;
  codeVerifier: string;
  nonce: string;
  next: string;
};

function flowConfig() {
  return {
    password: getSessionSecret(),
    name: "linkai_oauth_flow",
    maxAge: 60 * 10,
    cookie: cookieOptions,
  };
}

export async function writeOAuthFlow(data: OAuthFlowData): Promise<void> {
  const session = await useSession<OAuthFlowData>(flowConfig());
  await session.update(data);
}

/** Lê e invalida em seguida — o state é de uso único. */
export async function consumeOAuthFlow(): Promise<OAuthFlowData | null> {
  const session = await useSession<OAuthFlowData>(flowConfig());
  const data = session.data;
  await session.clear();
  if (!data || !data.state || !data.codeVerifier) return null;
  return data as OAuthFlowData;
}