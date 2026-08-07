/**
 * Configuração do Ariia (Identity Provider).
 *
 * Server-only: todas as leituras de `process.env` acontecem dentro de funções,
 * porque no runtime de Workers o ambiente é injetado por requisição.
 */

export type AriiaConfig = {
  issuerUrl: string;
  clientId: string;
  redirectUri: string;
  appBaseUrl: string;
};

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(
      `Variável de ambiente ausente: ${name}. Configure-a antes de usar o login do Ariia.`,
    );
  }
  return value;
}

export function getAriiaConfig(): AriiaConfig {
  return {
    issuerUrl: requireEnv("ARIIA_ISSUER_URL").replace(/\/+$/, ""),
    clientId: requireEnv("ARIIA_OAUTH_CLIENT_ID"),
    redirectUri: requireEnv("ARIIA_REDIRECT_URI"),
    appBaseUrl: requireEnv("APP_BASE_URL").replace(/\/+$/, ""),
  };
}

/**
 * Redirect URIs registrados no client do Ariia.
 *
 * `ARIIA_REDIRECT_URI` é o oficial (domínio principal: linkai.2lock.app.br).
 * `ARIIA_REDIRECT_URIS` (opcional, separado por vírgula) permite manter
 * domínios alternativos registrados sem trocar o principal.
 */
export function getRegisteredRedirectUris(): string[] {
  const primary = requireEnv("ARIIA_REDIRECT_URI");
  const extra = (process.env["ARIIA_REDIRECT_URIS"] ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  return [primary, ...extra.filter((value) => value !== primary)];
}

/**
 * Escolhe o redirect_uri registrado que casa com o host da requisição atual.
 * Sem correspondência, usa o oficial — o fluxo sempre volta para o app.br.
 */
export function resolveRedirectUri(requestUrl: string): string {
  const registered = getRegisteredRedirectUris();
  let host: string;
  try {
    host = new URL(requestUrl).host;
  } catch {
    return registered[0]!;
  }

  const match = registered.find((uri) => {
    try {
      return new URL(uri).host === host;
    } catch {
      return false;
    }
  });

  return match ?? registered[0]!;
}

/** Origem pública correspondente a um redirect_uri registrado. */
export function originOfRedirectUri(redirectUri: string): string {
  try {
    return new URL(redirectUri).origin;
  } catch {
    return getAriiaConfig().appBaseUrl;
  }
}

export function getSessionSecret(): string {
  return requireEnv("ARIIA_SESSION_SECRET");
}

/**
 * Escopos OIDC solicitados ao Ariia — identidade + `offline_access`, necessário
 * para receber refresh_token e revalidar a sessão sem novo consentimento.
 */
export const ARIIA_SCOPES = "openid email profile offline_access";

/**
 * Só aceita destinos internos. Impede open redirect via `?next=`.
 */
export function sanitizeNextPath(next: string | null | undefined): string {
  if (!next) return "/dashboard";
  if (!next.startsWith("/")) return "/dashboard";
  if (next.startsWith("//")) return "/dashboard";
  if (next.startsWith("/auth/") || next.startsWith("/api/")) return "/dashboard";
  return next;
}