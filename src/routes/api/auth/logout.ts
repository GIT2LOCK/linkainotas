/**
 * Encerra a Sessão B (Supabase) e a Sessão A (Ariia) e volta para a home.
 */
import { createFileRoute } from "@tanstack/react-router";

import { clearAriiaSession, readAriiaSession } from "@/lib/auth/ariia-session.server";
import { revokeAriiaToken } from "@/lib/auth/ariia-oauth.server";
import { destroySupabaseSession } from "@/lib/auth/session-bridge.server";

async function handleLogout(): Promise<Response> {
  // Revoga o refresh token no Ariia antes de descartar a Sessão A.
  const ariia = await readAriiaSession();
  if (ariia?.refreshToken) await revokeAriiaToken(ariia.refreshToken);

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