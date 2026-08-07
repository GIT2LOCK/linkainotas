/**
 * Server functions da autenticação.
 * Arquivo fino por contrato: apenas declarações de server fn.
 */
import { createServerFn } from "@tanstack/react-start";

import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

export const startAriiaLogin = createServerFn({ method: "POST" })
  .inputValidator((input: { origin: string; redirectTo?: string | undefined }) => input)
  .handler(async ({ data }) => {
    const { beginLogin } = await import("./login.server");
    return beginLogin(data);
  });

export const completeAriiaLogin = createServerFn({ method: "POST" })
  .inputValidator((input: { code: string; state: string }) => input)
  .handler(async ({ data }) => {
    const { finishLogin } = await import("./login.server");
    return finishLogin(data);
  });

export const getMyProfile = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { data, error } = await context.supabase
      .from("profiles")
      .select("id, ariia_user_id, nome, email, avatar_url, last_sync_at")
      .eq("id", context.userId)
      .maybeSingle();

    if (error) throw new Error(error.message);
    return data;
  });