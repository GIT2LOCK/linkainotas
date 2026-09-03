/**
 * O bucket linkai-avatars é privado. O servidor converte o caminho salvo em
 * usuarios.avatar_url em uma URL assinada antes de entregar ao navegador.
 */
const AVATAR_BUCKET = "linkai-avatars";
const SIGNED_URL_TTL_SECONDS = 60 * 60 * 24 * 7;

export async function resolveAvatarUrl(value: string | null): Promise<string | null> {
  if (!value) return null;
  if (/^https?:\/\//i.test(value)) return value;

  try {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data, error } = await supabaseAdmin.storage
      .from(AVATAR_BUCKET)
      .createSignedUrl(value.replace(/^linkai-avatars\//, ""), SIGNED_URL_TTL_SECONDS);
    if (error) return null;
    return data?.signedUrl ?? null;
  } catch {
    return null;
  }
}
