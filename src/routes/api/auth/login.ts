/**
 * Início do fluxo OAuth PKCE: gera state/nonce/code_verifier, guarda em cookie
 * httpOnly efêmero e redireciona para o Ariia.
 */
import { createFileRoute } from "@tanstack/react-router";

import { resolveRedirectUri, sanitizeNextPath } from "@/lib/auth/ariia-config.server";
import { buildAuthorizeUrl, createPkcePair, randomUrlSafeToken } from "@/lib/auth/ariia-oauth.server";
import { writeOAuthFlow } from "@/lib/auth/ariia-session.server";

export const Route = createFileRoute("/api/auth/login")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        try {
          const next = sanitizeNextPath(new URL(request.url).searchParams.get("next"));
          const redirectUri = resolveRedirectUri(request.url);
          const state = randomUrlSafeToken(32);
          const nonce = randomUrlSafeToken(16);
          const { verifier, challenge } = await createPkcePair();

          await writeOAuthFlow({ state, codeVerifier: verifier, nonce, next, redirectUri });

          const authorizeUrl = await buildAuthorizeUrl({
            state,
            nonce,
            codeChallenge: challenge,
            redirectUri,
          });

          // Diagnóstico: valor exato enviado ao Ariia (sem segredos).
          console.log("[Ariia][authorize] redirect_uri=", JSON.stringify(redirectUri));
          console.log("[Ariia][authorize] request_host=", new URL(request.url).host);
          console.log("[Ariia][authorize] url=", authorizeUrl);

          return new Response(null, {
            status: 302,
            headers: { location: authorizeUrl, "cache-control": "no-store" },
          });
        } catch (error) {
          console.error("[Ariia] Falha ao iniciar login:", error);
          return new Response(null, {
            status: 302,
            headers: { location: "/auth/error?reason=start_failed" },
          });
        }
      },
    },
  },
});