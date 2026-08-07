/**
 * Redirect URI registrado no Ariia: /auth/callback
 *
 * Orquestra: valida state -> troca o code -> verifica id_token -> provisiona o
 * usuário-espelho -> abre a sessão nativa Supabase -> grava a Sessão A.
 */
import { createFileRoute } from "@tanstack/react-router";

import { getAriiaConfig, sanitizeNextPath } from "@/lib/auth/ariia-config.server";
import { fetchAriiaUserInfo, readTokenExpiry, verifyAriiaIdToken } from "@/lib/auth/ariia-jwks.server";
import { exchangeAuthorizationCode } from "@/lib/auth/ariia-oauth.server";
import { consumeOAuthFlow, writeAriiaSession } from "@/lib/auth/ariia-session.server";
import { establishSupabaseSession } from "@/lib/auth/session-bridge.server";
import { ensureShadowUser } from "@/lib/auth/shadow-user.server";

function redirectTo(location: string): Response {
  return new Response(null, {
    status: 302,
    headers: { location, "cache-control": "no-store" },
  });
}

export const Route = createFileRoute("/auth/callback")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const url = new URL(request.url);
        const providerError = url.searchParams.get("error");
        if (providerError) {
          console.error(`[Ariia] callback com erro do IdP: ${providerError}`);
          return redirectTo(`/auth/error?reason=${encodeURIComponent(providerError)}`);
        }

        const code = url.searchParams.get("code");
        const state = url.searchParams.get("state");
        if (!code || !state) return redirectTo("/auth/error?reason=missing_code");

        const flow = await consumeOAuthFlow();
        if (!flow) return redirectTo("/auth/error?reason=expired_state");
        if (flow.state !== state) return redirectTo("/auth/error?reason=state_mismatch");

        try {
          const tokens = await exchangeAuthorizationCode({
            code,
            codeVerifier: flow.codeVerifier,
          });

          const identity = tokens.id_token
            ? await verifyAriiaIdToken({ idToken: tokens.id_token, expectedNonce: flow.nonce })
            : await fetchAriiaUserInfo(tokens.access_token);

          const user = await ensureShadowUser(identity);

          await establishSupabaseSession(user.email);

          const expiresAt =
            readTokenExpiry(tokens.access_token) ??
            (tokens.expires_in ? Math.floor(Date.now() / 1000) + tokens.expires_in : null);

          await writeAriiaSession({
            ariiaSub: identity.sub,
            email: user.email,
            name: user.nome,
            picture: user.avatarUrl,
            refreshToken: tokens.refresh_token ?? null,
            accessTokenExpiresAt: expiresAt,
            authUserId: user.authUserId,
            issuedAt: Math.floor(Date.now() / 1000),
          });

          // Mantém o redirecionamento no mesmo host público do app.
          const { appBaseUrl } = getAriiaConfig();
          return redirectTo(`${appBaseUrl}${sanitizeNextPath(flow.next)}`);
        } catch (error) {
          const reason = error instanceof Error && error.message === "INACTIVE_USER"
            ? "inactive_user"
            : "callback_failed";
          console.error("[Ariia] Falha no callback:", error);
          return redirectTo(`/auth/error?reason=${reason}`);
        }
      },
    },
  },
});