/**
 * Cliente Supabase do browser para PostgREST, Storage e Realtime.
 *
 * O Linkai não guarda tokens em localStorage: a sessão vive em cookies
 * httpOnly e o access token é buscado sob demanda no servidor. Por isso este
 * cliente usa `accessToken` e não expõe `supabase.auth.*`.
 */
import { createClient } from "@supabase/supabase-js";

import { getSupabaseAccessToken } from "@/lib/auth/session.functions";

import type { Database } from "./types";

const CACHE_MARGIN_MS = 30_000;

let cached: { token: string; fetchedAt: number } | null = null;

async function resolveAccessToken(): Promise<string> {
  if (cached && Date.now() - cached.fetchedAt < CACHE_MARGIN_MS) return cached.token;

  const { accessToken } = await getSupabaseAccessToken();
  if (!accessToken) {
    cached = null;
    return "";
  }

  cached = { token: accessToken, fetchedAt: Date.now() };
  return accessToken;
}

/** Limpa o token em cache (usar após logout). */
export function clearAccessTokenCache(): void {
  cached = null;
}

export const supabaseBrowser = createClient<Database>(
  import.meta.env["VITE_SUPABASE_URL"] as string,
  import.meta.env["VITE_SUPABASE_PUBLISHABLE_KEY"] as string,
  {
    accessToken: resolveAccessToken,
  },
);
