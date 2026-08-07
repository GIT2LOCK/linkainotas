/**
 * Cliente Supabase de servidor ligado aos cookies httpOnly da requisição.
 *
 * É este cliente que carrega a Sessão B (sessão nativa do Linkai): ele lê,
 * renova e reescreve os cookies `sb-*` automaticamente, e todas as queries
 * passam por RLS como o usuário-espelho.
 */
import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { getCookies, setCookie } from "@tanstack/react-start/server";

import type { Database } from "./types";

const COOKIE_DEFAULTS: CookieOptions = {
  httpOnly: true,
  secure: true,
  sameSite: "lax",
  path: "/",
};

export function getSupabaseServerClient() {
  const supabaseUrl = process.env['SUPABASE_URL'];
  const supabaseKey = process.env['SUPABASE_PUBLISHABLE_KEY'] ?? process.env['SUPABASE_ANON_KEY'];

  if (!supabaseUrl || !supabaseKey) {
    throw new Error("SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY ausentes no ambiente do servidor.");
  }

  return createServerClient<Database>(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return Object.entries(getCookies() ?? {}).map(([name, value]) => ({
          name,
          value: value ?? "",
        }));
      },
      setAll(cookiesToSet) {
        for (const { name, value, options } of cookiesToSet) {
          setCookie(name, value, { ...COOKIE_DEFAULTS, ...options });
        }
      },
    },
  });
}