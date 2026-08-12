/**
 * Sessão do Linkai espelhando a sessão do Ariia.
 *
 * Cookie httpOnly cifrado, exclusivo do servidor. O Ariia é a fonte de verdade:
 * a sessão Supabase local só sobrevive enquanto o token do Ariia for válido.
 */
import { useSession } from "@tanstack/react-start/server";

import { getSessionSecret } from "./ariia-config.server";

export type AriiaSessionData = {
  ariiaUserId: string;
  email: string;
  name: string | null;
  picture: string | null;
  permissao: string | null;
  /** Token da sessão customizada do Ariia. */
  ariiaToken: string;
  /** Epoch em segundos. */
  tokenExpiresAt: number | null;
  authUserId: string;
  issuedAt: number;
};

const MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

const cookieOptions = {
  httpOnly: true,
  secure: true,
  // "none" mantém a sessão válida também dentro do preview em iframe (cross-site).
  sameSite: "none" as const,
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
  if (!data || !data.ariiaUserId || !data.authUserId) return null;
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

/**
 * Sessão válida = cookie presente e token do Ariia não expirado. Sem token
 * válido no Ariia, derrubamos também a sessão Supabase local.
 */
export async function getValidAriiaSession(): Promise<AriiaSessionData | null> {
  const session = await readAriiaSession();
  if (!session) return null;

  const now = Math.floor(Date.now() / 1000);
  if (session.tokenExpiresAt && session.tokenExpiresAt <= now) {
    const { destroySupabaseSession } = await import("./session-bridge.server");
    await destroySupabaseSession();
    await clearAriiaSession();
    return null;
  }

  return session;
}

/**
 * Estado efêmero do 2FA. O challengeToken/setupToken nunca vai para o browser:
 * fica neste cookie cifrado de curta duração.
 */
export type PendingTwoFactor = {
  mode: "login" | "signup";
  challengeToken?: string;
  setupToken?: string;
  email: string;
};

function pendingConfig() {
  return {
    password: getSessionSecret(),
    name: "linkai_2fa",
    maxAge: 60 * 30,
    cookie: cookieOptions,
  };
}

export async function writePendingTwoFactor(data: PendingTwoFactor): Promise<void> {
  const session = await useSession<PendingTwoFactor>(pendingConfig());
  await session.update(data);
}

export async function readPendingTwoFactor(): Promise<PendingTwoFactor | null> {
  const session = await useSession<PendingTwoFactor>(pendingConfig());
  const data = session.data;
  if (!data || !data.mode) return null;
  return data as PendingTwoFactor;
}

export async function clearPendingTwoFactor(): Promise<void> {
  const session = await useSession<PendingTwoFactor>(pendingConfig());
  await session.clear();
}