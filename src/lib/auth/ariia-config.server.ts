/**
 * Configuração do Ariia (backend central de autenticação).
 *
 * Server-only: todas as leituras de `process.env` acontecem dentro de funções,
 * porque no runtime de Workers o ambiente é injetado por requisição.
 */

export type AriiaConfig = {
  /** Base das Edge Functions do Ariia, ex.: https://xxx.supabase.co/functions/v1 */
  functionsBaseUrl: string;
  anonKey: string;
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

export function getAriiaConfig(): AriiaConfig {
  const raw = requireEnv("ARIIA_ISSUER_URL").replace(/\/+$/, "");
  // O secret pode apontar para o issuer OIDC (…/auth/v1); as functions ficam na origem.
  let origin = raw;
  try {
    origin = new URL(raw).origin;
  } catch {
    origin = raw.replace(/\/(auth|functions)\/v1$/, "");
  }
  const appBaseUrl = (process.env['APP_BASE_URL'] ?? "").trim().replace(/\/+$/, "");

  return {
    functionsBaseUrl: `${origin}/functions/v1`,
    anonKey: requireEnv("ARIIA_ANON_KEY"),
    appBaseUrl,
  };
}

export function getSessionSecret(): string {
  return requireEnv("ARIIA_SESSION_SECRET");
}

/** Só aceita destinos internos. Impede open redirect. */
export function sanitizeNextPath(next: string | null | undefined): string {
  if (!next) return "/dashboard";
  if (!next.startsWith("/")) return "/dashboard";
  if (next.startsWith("//")) return "/dashboard";
  if (next.startsWith("/api/")) return "/dashboard";
  return next;
}