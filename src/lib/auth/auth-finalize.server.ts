/**
 * Traduz o resultado do Ariia em passo de UI e, quando autenticado, abre a
 * sessão local do Linkai (usuário-espelho + sessão nativa Supabase).
 * Server-only.
 */
import type { AriiaAuthResult } from "./ariia-api.server";
import type { AuthStep } from "./auth.functions";

export async function finalizeAriiaResult(
  result: AriiaAuthResult,
  mode: "login" | "signup",
  email: string,
): Promise<AuthStep> {
  const { writePendingTwoFactor, clearPendingTwoFactor, writeAriiaSession } =
    await import("./ariia-session.server");

  if (result.kind === "requires2FA") {
    await writePendingTwoFactor({ mode: "login", challengeToken: result.challengeToken, email });
    return { step: "2fa", message: result.message };
  }

  if (result.kind === "requiresSetup2FA") {
    await writePendingTwoFactor({ mode: "signup", setupToken: result.setupToken, email });
    const { ariiaSetupTwoFactor } = await import("./ariia-api.server");
    const setup = await ariiaSetupTwoFactor(result.setupToken);
    return {
      step: "setup2fa",
      message: result.message,
      secret: setup.secret,
      otpauthUrl: setup.otpauthUrl,
      qrCodeUrl: setup.qrCodeUrl,
    };
  }

  const { ensureShadowUser } = await import("./shadow-user.server");
  const user = await ensureShadowUser(result.identity);

  const { establishSupabaseSession } = await import("./session-bridge.server");
  await establishSupabaseSession(user.email);

  await writeAriiaSession({
    ariiaUserId: result.identity.sub,
    email: user.email,
    name: user.nome,
    picture: user.avatarUrl,
    permissao: user.perfilInterno,
    ariiaToken: result.session.token,
    tokenExpiresAt: result.session.expiresAt,
    authUserId: user.authUserId,
    issuedAt: Math.floor(Date.now() / 1000),
  });

  await clearPendingTwoFactor();
  void mode;
  return { step: "authenticated" };
}
