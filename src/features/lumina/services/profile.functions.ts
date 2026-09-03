import { createServerFn } from "@tanstack/react-start";

import { requireLinkaiUser } from "@/lib/auth/require-user";
import type { Database } from "@/integrations/supabase/types";

export type MeuPerfil = {
  authUserId: string;
  usuarioId: number;
  nome: string;
  email: string;
  avatarUrl: string | null;
  empresaNome: string | null;
  perfilCodigo: string;
  perfilNome: string;
  obras: Array<{
    id: string;
    codigo: string;
    nome: string;
    tipo: string;
    perfilNome: string;
    principal: boolean;
  }>;
  luminaUsername: string | null;
  luminaPasswordSet: boolean;
  luminaCredentialsUpdatedAt: string | null;
};

type ProfileUserRow = Pick<
  Database["public"]["Tables"]["usuarios"]["Row"],
  | "id"
  | "auth_user_id"
  | "nome"
  | "email"
  | "avatar_url"
  | "empresa_id"
  | "lumina_username"
  | "lumina_password_set"
  | "lumina_credentials_updated_at"
>;

const PROFILE_COLUMNS =
  "id, auth_user_id, nome, email, avatar_url, empresa_id, lumina_username, lumina_password_set, lumina_credentials_updated_at";

function requiredText(value: unknown, field: string, maxLength: number): string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`Informe ${field}.`);
  }

  return value.trim().slice(0, maxLength);
}

/** Returns only the current user's non-sensitive profile and credential status. */
export const getMeuPerfil = createServerFn({ method: "GET" })
  .middleware([requireLinkaiUser])
  .handler(async ({ context }): Promise<MeuPerfil> => {
    const [userResponse, linksResponse, profilesResponse] = await Promise.all([
      context.supabase.from("usuarios").select(PROFILE_COLUMNS).eq("id", context.user.id).single(),
      context.supabase
        .from("linkai_usuario_obras")
        .select("obra_id, perfil_codigo, principal, obra:linkai_obras(id, codigo, nome, tipo)")
        .eq("usuario_id", context.user.id)
        .eq("ativo", true)
        .order("principal", { ascending: false }),
      context.supabase.from("linkai_perfis_internos").select("codigo, nome"),
    ]);

    if (userResponse.error) throw userResponse.error;
    if (linksResponse.error) throw linksResponse.error;
    if (profilesResponse.error) throw profilesResponse.error;

    const user = userResponse.data as ProfileUserRow;
    const profileNames = new Map(
      (profilesResponse.data ?? []).map((profile) => [profile.codigo, profile.nome]),
    );
    const perfilCodigo = context.user.perfilInterno;

    const obras = (linksResponse.data ?? []).flatMap((row) => {
      const obra = row.obra as {
        id: string;
        codigo: string;
        nome: string;
        tipo: string;
      } | null;
      if (!obra) return [];

      return [
        {
          id: obra.id,
          codigo: obra.codigo,
          nome: obra.nome,
          tipo: obra.tipo,
          perfilNome: profileNames.get(row.perfil_codigo) ?? row.perfil_codigo,
          principal: row.principal === true,
        },
      ];
    });

    let empresaNome: string | null = null;
    if (user.empresa_id !== null) {
      const { data: empresa, error } = await context.supabase
        .from("empresas")
        .select("nome_fantasia")
        .eq("id", user.empresa_id)
        .maybeSingle();
      if (error) throw error;
      empresaNome = empresa?.nome_fantasia ?? null;
    }

    const { resolveAvatarUrl } = await import("@/lib/security/avatar-url.server");

    return {
      authUserId: user.auth_user_id,
      usuarioId: user.id,
      nome: user.nome,
      email: user.email,
      avatarUrl: await resolveAvatarUrl(user.avatar_url),
      empresaNome,
      perfilCodigo,
      perfilNome: profileNames.get(perfilCodigo) ?? perfilCodigo,
      obras,
      luminaUsername: user.lumina_username,
      luminaPasswordSet: user.lumina_password_set === true,
      luminaCredentialsUpdatedAt: user.lumina_credentials_updated_at,
    };
  });

/** Saves the initial Lumina login once; later changes are handled by support. */
export const saveMyInitialLuminaCredentials = createServerFn({ method: "POST" })
  .middleware([requireLinkaiUser])
  .validator((data: unknown) => {
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      throw new Error("Dados de credenciais inválidos.");
    }

    const candidate = data as { username?: unknown; password?: unknown };
    return {
      username: requiredText(candidate.username, "o usuário do Lumina", 120),
      password: requiredText(candidate.password, "a senha do Lumina", 240),
    };
  })
  .handler(async ({ context, data }) => {
    const encryptionSecret = process.env["LINKAI_LUMINA_CREDENTIALS_KEY"];
    if (!encryptionSecret) {
      throw new Error(
        "O armazenamento seguro do login Lumina ainda não foi configurado no ambiente publicado.",
      );
    }

    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { encryptLuminaSecret } = await import("@/lib/security/lumina-credentials.server");
    const passwordCiphertext = await encryptLuminaSecret(data.password, encryptionSecret);
    const updatedAt = new Date().toISOString();
    const { data: saved, error } = await supabaseAdmin
      .from("usuarios")
      .update({
        lumina_username: data.username,
        lumina_password_ciphertext: passwordCiphertext,
        lumina_password_set: true,
        lumina_credentials_updated_at: updatedAt,
      })
      .eq("id", context.user.id)
      .eq("lumina_password_set", false)
      .select("lumina_username, lumina_password_set, lumina_credentials_updated_at")
      .maybeSingle();
    if (error) throw error;
    if (!saved) {
      throw new Error(
        "A troca do login Lumina depende do atendimento técnico. Solicite a alteração pelo Meu Perfil.",
      );
    }

    await context.supabase.rpc("linkai_log_activity", {
      p_action: "profile.lumina_credentials.created",
      p_status: "info",
      p_payload: { username: data.username },
      p_message: "Credenciais iniciais do Lumina cadastradas pelo usuário.",
    });

    return {
      luminaUsername: data.username,
      luminaPasswordSet: true,
      luminaCredentialsUpdatedAt: updatedAt,
    };
  });

export const updateMyAvatar = createServerFn({ method: "POST" })
  .middleware([requireLinkaiUser])
  .validator((data: unknown) => {
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      throw new Error("Caminho da foto inválido.");
    }

    const path = (data as { path?: unknown }).path;
    if (typeof path !== "string" || path.trim().length === 0 || path.includes("..")) {
      throw new Error("Caminho da foto inválido.");
    }

    return { path: path.trim().slice(0, 240) };
  })
  .handler(async ({ context, data }) => {
    const expectedPrefix = `${context.authUserId}/`;
    if (!data.path.startsWith(expectedPrefix)) {
      throw new Error("A foto precisa pertencer ao usuário autenticado.");
    }

    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { error } = await supabaseAdmin
      .from("usuarios")
      .update({ avatar_url: data.path, avatar_customized: true })
      .eq("id", context.user.id);
    if (error) throw error;

    const { resolveAvatarUrl } = await import("@/lib/security/avatar-url.server");
    const avatarUrl = await resolveAvatarUrl(data.path);

    await context.supabase.rpc("linkai_log_activity", {
      p_action: "profile.avatar.updated",
      p_status: "info",
      p_payload: {},
      p_message: "Foto de perfil atualizada.",
    });

    return { avatarUrl };
  });
