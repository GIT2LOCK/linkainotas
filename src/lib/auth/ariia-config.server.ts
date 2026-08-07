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
  const raw = process.env[name];
  // Remove espaços e aspas acidentais vindas do painel de secrets.
  const value = raw?.trim().replace(/^["']|["']$/g, "");
  if (!value) {
    throw new Error(
      `Variável de ambiente ausente: ${name}. Configure-a antes de usar o login do Ariia.`,
    );
  }
  return value;
}

/**
 * Normaliza um redirect_uri para o formato exato registrado no Ariia:
 * sem espaços, sem barra final, sem query/hash.
 */
function normalizeRedirectUri(value: string): string {
  const cleaned = value.trim().replace(/\/+$/, "");
  try {
    const url = new URL(cleaned);
    url.search = "";
    url.hash = "";
    return `${url.origin}${url.pathname.replace(/\/+$/, "")}`;
  } catch {
    return cleaned;
  }
}

export function getAriiaConfig(): AriiaConfig {
  return {
    issuerUrl: requireEnv("ARIIA_ISSUER_URL").replace(/\/+$/, ""),
    clientId: requireEnv("ARIIA_OAUTH_CLIENT_ID"),
    redirectUri: normalizeRedirectUri(requireEnv("ARIIA_REDIRECT_URI")),
    appBaseUrl: requireEnv("APP_BASE_URL").replace(/\/+$/, ""),
  };
}

/**
 * Redirect URIs registrados no client do Ariia.
 *
 * O client do Ariia registra APENAS `https://linkai.2lock.app.br/auth/callback`.
 * Portanto existe um único valor válido: `ARIIA_REDIRECT_URI`. Nenhuma outra
 * variável pode sobrescrevê-lo e nenhum host de requisição altera o valor.
 */
export function getRegisteredRedirectUris(): string[] {
  return [getAriiaConfig().redirectUri];
}

/**
 * Sempre retorna o único redirect_uri registrado — independentemente do host
 * da requisição (preview, localhost ou domínio oficial). O Ariia exige match
 * exato, então este valor é o mesmo no authorize e na troca do code.
 */
export function resolveRedirectUri(_requestUrl?: string): string {
  return getAriiaConfig().redirectUri;
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