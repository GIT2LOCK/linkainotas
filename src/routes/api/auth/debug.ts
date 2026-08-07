/**
 * Diagnóstico do fluxo OAuth do Ariia.
 *
 * Mostra o `redirect_uri` exato e a URL completa de authorize que o Linkai
 * envia — sem expor segredos (client_id é público; state/nonce/PKCE são
 * valores descartáveis gerados só para esta inspeção).
 */
import { createFileRoute } from "@tanstack/react-router";

import { getAriiaConfig, resolveRedirectUri } from "@/lib/auth/ariia-config.server";
import { buildAuthorizeUrl, createPkcePair, getDiscovery, randomUrlSafeToken } from "@/lib/auth/ariia-oauth.server";

export const Route = createFileRoute("/api/auth/debug")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        try {
          const config = getAriiaConfig();
          const discovery = await getDiscovery(config);
          const redirectUri = resolveRedirectUri(request.url);
          const { challenge } = await createPkcePair();
          const authorizeUrl = await buildAuthorizeUrl({
            state: randomUrlSafeToken(32),
            nonce: randomUrlSafeToken(16),
            codeChallenge: challenge,
            redirectUri,
          });

          const rawEnv = process.env["ARIIA_REDIRECT_URI"] ?? null;
          const probe = await fetch(authorizeUrl, { redirect: "manual" });
          const probeBody = probe.status >= 400 ? (await probe.text()).slice(0, 300) : null;

          return Response.json(
            {
              request_host: new URL(request.url).host,
              redirect_uri_enviado: redirectUri,
              redirect_uri_env_bruto: rawEnv,
              redirect_uri_igual_ao_env: rawEnv === redirectUri,
              tem_barra_final: redirectUri.endsWith("/"),
              protocolo: new URL(redirectUri).protocol,
              authorize_endpoint: discovery.authorization_endpoint,
              authorize_url_completa: authorizeUrl,
              resposta_do_ariia: {
                status: probe.status,
                location: probe.headers.get("location"),
                body: probeBody,
              },
            },
            { headers: { "cache-control": "no-store" } },
          );
        } catch (error) {
          return Response.json(
            { erro: error instanceof Error ? error.message : String(error) },
            { status: 500 },
          );
        }
      },
    },
  },
});