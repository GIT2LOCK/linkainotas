/**
 * Espelhamento da identidade do Ariia no Supabase Auth local do Linkai.
 * O usuário nunca possui senha aqui: a sessão é criada por token de uso único.
 */
import type { AriiaIdentity, AriiaTokenSet } from "./ariia.server";
import { encryptString, requireEnv } from "./crypto.server";

export interface MirrorResult {
  userId: string;
  /** token_hash de uso único; o browser converte em sessão Supabase via verifyOtp. */
  tokenHash: string;
  email: string;
}

/**
 * 1. Garante o usuário em auth.users (sem senha, e-mail já confirmado).
 * 2. Atualiza metadados com os dados vindos do Ariia.
 * 3. Faz upsert em profiles e no vínculo server-only ariia_identities.
 * 4. Emite um token de uso único para o browser abrir a sessão Supabase.
 */
export async function mirrorAriiaIdentity(
  identity: AriiaIdentity,
  tokens: AriiaTokenSet,
): Promise<MirrorResult> {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");

  const userMetadata = {
    ariia_user_id: identity.ariiaUserId,
    provider: "ariia",
    nome: identity.nome,
    full_name: identity.nome,
    avatar_url: identity.avatarUrl,
  };

  const created = await supabaseAdmin.auth.admin.createUser({
    email: identity.email,
    email_confirm: true,
    user_metadata: userMetadata,
    app_metadata: { provider: "ariia", ariia_user_id: identity.ariiaUserId },
  });

  const alreadyExisted = Boolean(created.error);
  if (created.error && !/already|exists|registered/i.test(created.error.message)) {
    throw new Error(`Não foi possível espelhar o usuário: ${created.error.message}`);
  }

  // generateLink devolve o usuário (novo ou existente) e o token de uso único.
  const linked = await supabaseAdmin.auth.admin.generateLink({
    type: "magiclink",
    email: identity.email,
  });

  if (linked.error || !linked.data?.user) {
    throw new Error(
      `Não foi possível criar a sessão local: ${linked.error?.message ?? "usuário não encontrado"}`,
    );
  }

  const userId = linked.data.user.id;
  const tokenHash = linked.data.properties?.hashed_token;
  if (!tokenHash) throw new Error("Backend não devolveu o token de sessão.");

  if (alreadyExisted) {
    await supabaseAdmin.auth.admin.updateUserById(userId, {
      email_confirm: true,
      user_metadata: userMetadata,
      app_metadata: { provider: "ariia", ariia_user_id: identity.ariiaUserId },
    });
  }

  const nowIso = new Date().toISOString();

  const { error: profileError } = await supabaseAdmin.from("profiles").upsert(
    {
      id: userId,
      ariia_user_id: identity.ariiaUserId,
      nome: identity.nome,
      email: identity.email,
      avatar_url: identity.avatarUrl,
      last_sync_at: nowIso,
      updated_at: nowIso,
    },
    { onConflict: "id" },
  );
  if (profileError) throw new Error(`Falha ao sincronizar o perfil: ${profileError.message}`);

  const refreshTokenEncrypted = tokens.refresh_token
    ? await encryptString(tokens.refresh_token, requireEnv("ARIIA_TOKEN_ENC_KEY"))
    : null;

  const { error: identityError } = await supabaseAdmin.from("ariia_identities").upsert(
    {
      user_id: userId,
      ariia_user_id: identity.ariiaUserId,
      refresh_token_encrypted: refreshTokenEncrypted,
      expires_at: tokens.expires_in
        ? new Date(Date.now() + tokens.expires_in * 1000).toISOString()
        : null,
      last_login_at: nowIso,
      updated_at: nowIso,
    },
    { onConflict: "user_id" },
  );
  if (identityError) {
    throw new Error(`Falha ao vincular a identidade do Ariia: ${identityError.message}`);
  }

  return { userId, tokenHash, email: identity.email };
}