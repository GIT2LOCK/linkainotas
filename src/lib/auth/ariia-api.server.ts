/**
 * Cliente HTTP das Edge Functions de autenticação do Ariia.
 *
 * O Ariia é o backend central de autenticação: senha, 2FA e cadastro são
 * executados lá. O Linkai apenas repassa as credenciais e consome o resultado.
 * Server-only.
 */
import { getAriiaConfig } from "./ariia-config.server";
import type { AriiaIdentity, AriiaSessionToken } from "./identity";

export class AriiaAuthError extends Error {
  status: number;
  constructor(message: string, status = 400) {
    super(message);
    this.name = "AriiaAuthError";
    this.status = status;
  }
}

type AriiaUser = {
  id: number | string;
  nome?: string | null;
  email: string;
  permissao?: string | null;
  avatar_url?: string | null;
};

type AriiaEnvelope = {
  success?: boolean;
  message?: string;
  error?: string;
  user?: AriiaUser;
  session?: { token: string; expires_at?: string | null };
  requires2FA?: boolean;
  userId?: number | string;
  challengeToken?: string;
  requiresSetup2FA?: boolean;
  setupToken?: string;
  secret?: string;
  otpauthUrl?: string;
  qrCodeUrl?: string;
};

async function callAriia(path: string, body: unknown): Promise<AriiaEnvelope> {
  const { functionsBaseUrl, anonKey } = getAriiaConfig();

  const response = await fetch(`${functionsBaseUrl}/${path}`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "application/json",
      apikey: anonKey,
      authorization: `Bearer ${anonKey}`,
    },
    body: JSON.stringify(body),
  });

  const text = await response.text();
  let payload: AriiaEnvelope = {};
  try {
    payload = text ? (JSON.parse(text) as AriiaEnvelope) : {};
  } catch {
    console.error(`[Ariia] resposta não-JSON de ${path} (${response.status})`);
    throw new AriiaAuthError("Resposta inválida do Ariia.", 502);
  }

  if (!response.ok || payload.success === false) {
    const message = payload.error ?? payload.message ?? "Não foi possível concluir a operação.";
    throw new AriiaAuthError(message, response.status || 400);
  }

  return payload;
}

export function toIdentity(user: AriiaUser): AriiaIdentity {
  return {
    sub: String(user.id),
    email: user.email,
    name: user.nome ?? null,
    picture: user.avatar_url ?? null,
    permissao: user.permissao ?? null,
  };
}

function toSessionToken(session: { token: string; expires_at?: string | null }): AriiaSessionToken {
  const parsed = session.expires_at ? Date.parse(session.expires_at) : Number.NaN;
  return {
    token: session.token,
    expiresAt: Number.isNaN(parsed) ? null : Math.floor(parsed / 1000),
  };
}

export type AriiaAuthResult =
  | { kind: "authenticated"; identity: AriiaIdentity; session: AriiaSessionToken }
  | { kind: "requires2FA"; challengeToken: string; message: string }
  | { kind: "requiresSetup2FA"; setupToken: string; message: string };

function interpret(payload: AriiaEnvelope): AriiaAuthResult {
  if (payload.requires2FA && payload.challengeToken) {
    return {
      kind: "requires2FA",
      challengeToken: payload.challengeToken,
      message: payload.message ?? "Verificação 2FA necessária.",
    };
  }

  if (payload.requiresSetup2FA && payload.setupToken) {
    return {
      kind: "requiresSetup2FA",
      setupToken: payload.setupToken,
      message: payload.message ?? "Configure o 2FA para continuar.",
    };
  }

  if (payload.user && payload.session?.token) {
    return {
      kind: "authenticated",
      identity: toIdentity(payload.user),
      session: toSessionToken(payload.session),
    };
  }

  throw new AriiaAuthError("Resposta inesperada do Ariia.", 502);
}

/** POST /functions/v1/login */
export async function ariiaLogin(input: {
  email: string;
  senha: string;
}): Promise<AriiaAuthResult> {
  return interpret(await callAriia("login", { email: input.email, senha: input.senha }));
}

/** POST /functions/v1/signup */
export async function ariiaSignup(input: {
  nome: string;
  email: string;
  senha: string;
}): Promise<AriiaAuthResult> {
  return interpret(
    await callAriia("signup", { nome: input.nome, email: input.email, senha: input.senha }),
  );
}

/** POST /functions/v1/setup-2fa */
export async function ariiaSetupTwoFactor(setupToken: string): Promise<{
  secret: string;
  otpauthUrl: string;
  qrCodeUrl: string;
}> {
  const payload = await callAriia("setup-2fa", { setupToken });
  if (!payload.secret || !payload.otpauthUrl) {
    throw new AriiaAuthError("O Ariia não retornou o segredo do 2FA.", 502);
  }
  return {
    secret: payload.secret,
    otpauthUrl: payload.otpauthUrl,
    qrCodeUrl: payload.qrCodeUrl ?? "",
  };
}

/** POST /functions/v1/verify-2fa */
export async function ariiaVerifyTwoFactor(
  input:
    | { code: string; isSetup: true; setupToken: string }
    | { code: string; isSetup: false; challengeToken: string },
): Promise<AriiaAuthResult> {
  return interpret(await callAriia("verify-2fa", input));
}
