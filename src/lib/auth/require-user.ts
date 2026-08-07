/**
 * Middleware de server functions: exige Sessão A + Sessão B válidas.
 *
 * Injeta no contexto um cliente Supabase autenticado (RLS como o
 * usuário-espelho), o `authUserId` e o perfil Linkai já resolvido.
 */
import { createMiddleware } from "@tanstack/react-start";

export const requireLinkaiUser = createMiddleware({ type: "function" }).server(
  async ({ next }) => {
    const { getValidAriiaSession } = await import("./ariia-session.server");
    const ariia = await getValidAriiaSession();
    if (!ariia) throw new Response("Unauthorized", { status: 401 });

    const { getSupabaseServerClient } = await import(
      "@/integrations/supabase/server-session.server"
    );
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user) throw new Response("Unauthorized", { status: 401 });

    const { getLinkaiUserByAuthId } = await import("./shadow-user.server");
    const profile = await getLinkaiUserByAuthId(data.user.id);
    if (!profile || !profile.ativo) throw new Response("Forbidden", { status: 403 });

    return next({
      context: {
        supabase,
        authUserId: data.user.id,
        user: profile,
      },
    });
  },
);