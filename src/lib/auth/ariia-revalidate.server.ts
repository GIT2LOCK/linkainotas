/**
 * Revalidação da Sessão A contra o Ariia.
 *
 * O Ariia é a fonte de verdade: quando o access token dele expira, tentamos o
 * refresh_token. Se o Ariia recusar (acesso revogado, usuário desligado), as
 * duas sessões são derrubadas — a sessão nativa do Linkai nunca sobrevive à
 * perda da identidade no Ariia.
 */
import { refreshAriiaTokens } from "./ariia-oauth.server";
import {
  clearAriiaSession,
  readAriiaSession,
  writeAriiaSession,
  type AriiaSessionData,
} from "./ariia-session.server";

/** Margem para renovar antes do vencimento real. */
const SKEW_SECONDS = 60;

export async function getValidAriiaSession(): Promise<AriiaSessionData | null> {
  const session = await readAriiaSession();
  if (!session) return null;

  const now = Math.floor(Date.now() / 1000);
  const expiresAt = session.accessTokenExpiresAt;

  // Sem expiração conhecida, confiamos no maxAge do cookie cifrado.
  if (!expiresAt || expiresAt - SKEW_SECONDS > now) return session;

  if (!session.refreshToken) {
    await destroyAllSessions();
    return null;
  }

  try {
    const tokens = await refreshAriiaTokens(session.refreshToken);
    const nextExpiry = tokens.expires_in ? now + tokens.expires_in : null;

    const updated: AriiaSessionData = {
      ...session,
      refreshToken: tokens.refresh_token ?? session.refreshToken,
      accessTokenExpiresAt: nextExpiry,
      issuedAt: now,
    };
    await writeAriiaSession(updated);
    return updated;
  } catch (error) {
    console.error("[Ariia] Refresh recusado — encerrando sessões:", error);
    await destroyAllSessions();
    return null;
  }
}

async function destroyAllSessions(): Promise<void> {
  const { destroySupabaseSession } = await import("./session-bridge.server");
  await destroySupabaseSession();
  await clearAriiaSession();
}