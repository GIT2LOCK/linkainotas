/**
 * Encerra a Sessão B (Supabase) e a Sessão A (Ariia) e volta para a home.
 */
import { createFileRoute } from "@tanstack/react-router";

import { clearAriiaSession } from "@/lib/auth/ariia-session.server";
import { destroySupabaseSession } from "@/lib/auth/session-bridge.server";

async function handleLogout(): Promise<Response> {
  await destroySupabaseSession();
  await clearAriiaSession();
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