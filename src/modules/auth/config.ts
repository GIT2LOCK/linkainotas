/**
 * Configuração pública da integração OAuth com o Ariia (Identity Provider).
 * Nada aqui é secreto — pode ser importado no browser.
 */

/** URL base do Auth do Ariia (issuer canônico OIDC). */
export const ARIIA_AUTH_BASE_URL = "https://jjemlhtyhnncqzpnskor.supabase.co/auth/v1";

/** OAuth App (Public Client / PKCE) do Linkai registrado no Ariia. */
export const ARIIA_CLIENT_ID = "96f5d735-82dc-43d7-a534-b0288c8fa009";

/** Escopos solicitados no consentimento. */
export const ARIIA_SCOPES = "openid email profile offline_access";

/** Caminho do callback OAuth dentro do Linkai. */
export const AUTH_CALLBACK_PATH = "/auth/callback";

/** Rota inicial da área autenticada. */
export const AUTHENTICATED_HOME = "/dashboard";

/** Rota pública de entrada. */
export const SIGN_IN_PATH = "/";

/**
 * Origens autorizadas a montar o redirect_uri.
 * Produção + desenvolvimento local + previews do Lovable.
 */
export const ALLOWED_ORIGINS = [
  "https://linkai.2lock.com.br",
  "https://www.linkai.2lock.com.br",
] as const;

const ALLOWED_ORIGIN_PATTERNS = [
  /^http:\/\/localhost(:\d+)?$/,
  /^http:\/\/127\.0\.0\.1(:\d+)?$/,
  /^https:\/\/[a-z0-9-]+\.lovable\.app$/,
  /^https:\/\/[a-z0-9-]+\.lovableproject\.com$/,
];

export function isAllowedOrigin(origin: string): boolean {
  if ((ALLOWED_ORIGINS as readonly string[]).includes(origin)) return true;
  return ALLOWED_ORIGIN_PATTERNS.some((pattern) => pattern.test(origin));
}

/** Valida um caminho de retorno para evitar open redirect. */
export function sanitizeRedirectPath(value: string | null | undefined): string {
  if (!value) return AUTHENTICATED_HOME;
  if (!value.startsWith("/") || value.startsWith("//")) return AUTHENTICATED_HOME;
  if (value.startsWith(AUTH_CALLBACK_PATH)) return AUTHENTICATED_HOME;
  return value;
}