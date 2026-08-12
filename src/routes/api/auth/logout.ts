/**
 * Encerra a sessão local do Linkai (Supabase + cookie do Ariia) e volta à home.
 * O Ariia mantém sua própria sessão — aqui só descartamos a local.
 */
import { createFileRoute } from "@tanstack/react-router";

import { clearAriiaSession, clearPendingTwoFactor } from "@/lib/auth/ariia-session.server";
import { destroySupabaseSession } from "@/lib/auth/session-bridge.server";

async function handleLogout(): Promise<Response> {
  await destroySupabaseSession();
  await clearAriiaSession();
  await clearPendingTwoFactor();
  return new Response(null, {
    status: 302,
    headers: { location: "/", "cache-control": "no-store" },
  });
}

export const Route = createFileRoute("/api/auth/logout")({
  server: {
    handlers: {
      GET: handleLogout,
      POST: handleLogout,
    },
  },
});
