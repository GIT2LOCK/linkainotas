/**
 * Ponte de sessão: Ariia (Sessão A) -> sessão nativa Supabase do Linkai (Sessão B).
 *
 * Emite um magic link internamente (Admin API) e o consome no próprio servidor
 * com `verifyOtp`, produzindo access/refresh tokens legítimos do Linkai. Os
 * tokens ficam em cookies httpOnly gerenciados pelo cliente SSR do Supabase —
 * nunca em localStorage.
 */
import { supabaseAdmin } from "@/integrations/supabase/client.server";
import { getSupabaseServerClient } from "@/integrations/supabase/server-session.server";

export async function establishSupabaseSession(email: string): Promise<void> {
  const { data, error } = await supabaseAdmin.auth.admin.generateLink({
    type: "magiclink",
    email,
  });

  if (error) throw error;

  const tokenHash = data.properties?.hashed_token;
  if (!tokenHash) throw new Error("Admin API não retornou hashed_token para a ponte de sessão.");

  const supabase = getSupabaseServerClient();
  const { error: verifyError } = await supabase.auth.verifyOtp({
    type: "email",
    token_hash: tokenHash,
  });

  if (verifyError) throw verifyError;
}

export async function destroySupabaseSession(): Promise<void> {
  const supabase = getSupabaseServerClient();
  try {
    await supabase.auth.signOut();
  } catch (error) {
    console.error("[Linkai] Falha ao encerrar a sessão Supabase:", error);
  }
}
