/**
 * Server functions de autenticação do Linkai.
 *
 * Fluxo: o front envia e-mail/senha -> o servidor chama as Edge Functions do
 * Ariia -> se o Ariia autenticar, provisionamos o usuário-espelho e abrimos a
 * sessão nativa Supabase em cookies httpOnly. Sem redirects, sem consentimento.
 */
import { createServerFn } from "@tanstack/react-start";
import { codeSchema, credentialsSchema, signupSchema } from "./auth-schemas";

export type AuthStep =
  | { step: "authenticated" }
  | { step: "2fa"; message: string }
  | { step: "setup2fa"; message: string; secret: string; otpauthUrl: string; qrCodeUrl: string };

export const loginWithAriia = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) => credentialsSchema.parse(data))
  .handler(async ({ data }): Promise<AuthStep> => {
    const { ariiaLogin } = await import("./ariia-api.server");
    const result = await ariiaLogin(data);

    const { finalizeAriiaResult } = await import("./auth-finalize.server");
    return finalizeAriiaResult(result, "login", data.email);
  });

export const signupWithAriia = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) => signupSchema.parse(data))
  .handler(async ({ data }): Promise<AuthStep> => {
    const { ariiaSignup } = await import("./ariia-api.server");
    const result = await ariiaSignup(data);

    const { finalizeAriiaResult } = await import("./auth-finalize.server");
    return finalizeAriiaResult(result, "signup", data.email);
  });

export const verifyTwoFactor = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) => codeSchema.parse(data))
  .handler(async ({ data }): Promise<AuthStep> => {
    const { readPendingTwoFactor } = await import("./ariia-session.server");
    const pending = await readPendingTwoFactor();
    if (!pending) throw new Error("Sessão de verificação expirada. Faça login novamente.");

    const { ariiaVerifyTwoFactor } = await import("./ariia-api.server");
    const result =
      pending.mode === "signup" && pending.setupToken
        ? await ariiaVerifyTwoFactor({ code: data.code, isSetup: true, setupToken: pending.setupToken })
        : await ariiaVerifyTwoFactor({
            code: data.code,
            isSetup: false,
            challengeToken: pending.challengeToken ?? "",
          });

    const { finalizeAriiaResult } = await import("./auth-finalize.server");
    return finalizeAriiaResult(result, pending.mode, pending.email);
  });

export const signOut = createServerFn({ method: "POST" }).handler(async (): Promise<{ ok: true }> => {
  const { clearAriiaSession, clearPendingTwoFactor } = await import("./ariia-session.server");
  const { destroySupabaseSession } = await import("./session-bridge.server");
  await destroySupabaseSession();
  await clearAriiaSession();
  await clearPendingTwoFactor();
  return { ok: true };
});