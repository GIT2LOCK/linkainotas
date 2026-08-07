/**
 * Provisionamento do usuário-espelho.
 *
 * Cada identidade do Ariia ganha um usuário correspondente em `auth.users`
 * do Linkai e uma linha em `public.usuarios`. Assim `auth.uid()`, RLS,
 * Storage e Realtime continuam funcionando de forma nativa.
 *
 * Server-only: usa a service role. Nunca importar de código de cliente.
 */
import { supabaseAdmin } from "@/integrations/supabase/client.server";

import type { AriiaIdentity } from "./ariia-jwks.server";

export type LinkaiUser = {
  id: number;
  authUserId: string;
  ariiaUserId: string;
  nome: string;
  email: string;
  permissao: string | null;
  empresaId: number | null;
  avatarUrl: string | null;
  ativo: boolean;
};

/** Busca um usuário do GoTrue por e-mail via Admin API REST (filtro por e-mail). */
async function findAuthUserIdByEmail(email: string): Promise<string | null> {
  const supabaseUrl = process.env['SUPABASE_URL'];
  const serviceKey = process.env['SUPABASE_SERVICE_ROLE_KEY'];
  if (!supabaseUrl || !serviceKey) return null;

  const url = new URL(`${supabaseUrl}/auth/v1/admin/users`);
  url.searchParams.set("page", "1");
  url.searchParams.set("per_page", "50");
  url.searchParams.set("filter", email);

  const response = await fetch(url, {
    headers: {
      apikey: serviceKey,
      authorization: `Bearer ${serviceKey}`,
      accept: "application/json",
    },
  });

  if (!response.ok) {
    console.error(`[Linkai] admin/users ${response.status}: ${await response.text()}`);
    return null;
  }

  const body = (await response.json()) as { users?: Array<{ id: string; email?: string }> };
  const match = body.users?.find((user) => user.email?.toLowerCase() === email.toLowerCase());
  return match?.id ?? null;
}

async function createShadowAuthUser(identity: AriiaIdentity): Promise<string> {
  const { data, error } = await supabaseAdmin.auth.admin.createUser({
    email: identity.email,
    email_confirm: true,
    user_metadata: {
      full_name: identity.name ?? identity.email,
      avatar_url: identity.picture,
      ariia_sub: identity.sub,
    },
    app_metadata: {
      provider: "ariia",
      providers: ["ariia"],
      ariia_sub: identity.sub,
    },
  });

  if (!error && data.user) return data.user.id;

  // Conflito de e-mail: o usuário-espelho já existe (ex.: criado antes do vínculo).
  const existing = await findAuthUserIdByEmail(identity.email);
  if (existing) return existing;

  throw new Error(`Não foi possível provisionar o usuário-espelho: ${error?.message ?? "erro desconhecido"}`);
}

function mapRow(row: {
  id: number;
  auth_user_id: string;
  ariia_user_id: string | null;
  nome: string;
  email: string;
  permissao: string | null;
  empresa_id: number | null;
  avatar_url: string | null;
  ativo: boolean | null;
}): LinkaiUser {
  return {
    id: row.id,
    authUserId: row.auth_user_id,
    ariiaUserId: row.ariia_user_id ?? "",
    nome: row.nome,
    email: row.email,
    permissao: row.permissao,
    empresaId: row.empresa_id,
    avatarUrl: row.avatar_url,
    ativo: row.ativo !== false,
  };
}

const USER_COLUMNS =
  "id, auth_user_id, ariia_user_id, nome, email, permissao, empresa_id, avatar_url, ativo";

/**
 * Idempotente: resolve (ou cria) o usuário-espelho para a identidade do Ariia
 * e mantém nome/e-mail/avatar sincronizados a cada login.
 */
export async function ensureShadowUser(identity: AriiaIdentity): Promise<LinkaiUser> {
  const { data: byAriia, error: lookupError } = await supabaseAdmin
    .from("usuarios")
    .select(USER_COLUMNS)
    .eq("ariia_user_id", identity.sub)
    .maybeSingle();

  if (lookupError) throw lookupError;

  const authUserId =
    byAriia?.auth_user_id ??
    (await findAuthUserIdByEmail(identity.email)) ??
    (await createShadowAuthUser(identity));

  const nome = identity.name ?? identity.email.split("@")[0] ?? identity.email;

  const { data: upserted, error: upsertError } = await supabaseAdmin
    .from("usuarios")
    .upsert(
      {
        ...(byAriia ? { id: byAriia.id } : {}),
        auth_user_id: authUserId,
        ariia_user_id: identity.sub,
        nome,
        email: identity.email,
        avatar_url: identity.picture,
        atualizado_em: new Date().toISOString(),
      },
      { onConflict: "ariia_user_id" },
    )
    .select(USER_COLUMNS)
    .single();

  if (upsertError) throw upsertError;

  const user = mapRow(upserted);

  if (!user.ativo) {
    throw new Error("INACTIVE_USER");
  }

  return user;
}

/** Carrega o perfil Linkai a partir do id de `auth.users`. */
export async function getLinkaiUserByAuthId(authUserId: string): Promise<LinkaiUser | null> {
  const { data, error } = await supabaseAdmin
    .from("usuarios")
    .select(USER_COLUMNS)
    .eq("auth_user_id", authUserId)
    .maybeSingle();

  if (error) throw error;
  return data ? mapRow(data) : null;
}