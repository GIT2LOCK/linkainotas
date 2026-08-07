/**
 * Estado temporário do fluxo OAuth (state, nonce, code_verifier, destino).
 * Guardado em cookie httpOnly cifrado — o code_verifier nunca fica acessível ao JS.
 */
import { deleteCookie, getCookie, setCookie } from "@tanstack/react-start/server";

import { decryptString, encryptString, requireEnv } from "./crypto.server";

const COOKIE_NAME = "linkai_oauth_flow";
const MAX_AGE_SECONDS = 60 * 10;

export interface OAuthFlowState {
  state: string;
  nonce: string;
  codeVerifier: string;
  redirectUri: string;
  redirectTo: string;
  createdAt: number;
}

function secret(): string {
  return requireEnv("ARIIA_OAUTH_STATE_SECRET");
}

export async function saveFlowState(flow: OAuthFlowState): Promise<void> {
  const value = await encryptString(JSON.stringify(flow), secret());
  setCookie(COOKIE_NAME, value, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: MAX_AGE_SECONDS,
  });
}

export async function consumeFlowState(): Promise<OAuthFlowState | null> {
  const raw = getCookie(COOKIE_NAME);
  deleteCookie(COOKIE_NAME, { path: "/" });
  if (!raw) return null;

  try {
    const flow = JSON.parse(await decryptString(raw, secret())) as OAuthFlowState;
    if (Date.now() - flow.createdAt > MAX_AGE_SECONDS * 1000) return null;
    return flow;
  } catch (error) {
    console.error("[Ariia] estado OAuth inválido:", error);
    return null;
  }
}