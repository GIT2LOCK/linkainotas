/**
 * Server functions de sessão consumidas pelo front.
 *
 * Nenhum token trafega para o browser: apenas o perfil já resolvido, e o
 * access token sob demanda para PostgREST/Realtime/Storage no cliente.
 */
import { createServerFn } from "@tanstack/react-start";

export type SessionUser = {
  authUserId: string;
  nome: string;
  email: string;
  /** Perfil interno principal do LinkAI (superadmin_2lock, supervisor_empresa, ...). */
  permissao: string | null;
  perfilInterno: string;
  isPlatformSuperadmin: boolean;
  empresaId: number | null;
  avatarUrl: string | null;
};


function isMissingAriiaSessionConfig(error: unknown): boolean {
  return (
    error instanceof Error &&
    error.message.startsWith("Variável de ambiente ausente: ARIIA_SESSION_SECRET.")
  );
}

export const getCurrentSession = createServerFn({ method: "GET" }).handler(
  async (): Promise<{ user: SessionUser | null }> => {
    const { getValidAriiaSession } = await import("./ariia-session.server");
    let ariia;
    try {
      ariia = await getValidAriiaSession();
    } catch (error) {
      if (isMissingAriiaSessionConfig(error)) return { user: null };
      throw error;
    }
    if (!ariia) return { user: null };

    const { getSupabaseServerClient } =
      await import("@/integrations/supabase/server-session.server");
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user) return { user: null };

    const { getLinkaiUserByAuthId } = await import("./shadow-user.server");
    const profile = await getLinkaiUserByAuthId(data.user.id);
    if (!profile || !profile.ativo) return { user: null };

    return {
      user: {
        authUserId: profile.authUserId,
        nome: profile.nome,
        email: profile.email,
        permissao: profile.permissao,
        empresaId: profile.empresaId,
        avatarUrl: profile.avatarUrl,
      },
    };
  },
);

/**
 * Entrega o access token da Sessão B para o cliente Supabase do browser.
 * O refresh continua sendo feito no servidor, nos cookies httpOnly.
 */
export const getSupabaseAccessToken = createServerFn({ method: "GET" }).handler(
  async (): Promise<{ accessToken: string | null }> => {
    const { getValidAriiaSession } = await import("./ariia-session.server");
    if (!(await getValidAriiaSession())) return { accessToken: null };

    const { getSupabaseServerClient } =
      await import("@/integrations/supabase/server-session.server");
    const supabase = getSupabaseServerClient();
    const { data } = await supabase.auth.getSession();
    return { accessToken: data.session?.access_token ?? null };
  },
);
