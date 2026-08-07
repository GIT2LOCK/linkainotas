/**
 * Orquestração server-only do login OAuth PKCE com o Ariia.
 */
import {
  AUTH_CALLBACK_PATH,
  isAllowedOrigin,
  sanitizeRedirectPath,
} from "./config";
import {
  buildAuthorizationUrl,
  exchangeAuthorizationCode,
  resolveIdentity,
} from "./ariia.server";
import { createPkcePair, randomUrlSafeString } from "./crypto.server";
import { consumeFlowState, saveFlowState } from "./oauth-state.server";
import { mirrorAriiaIdentity } from "./sync.server";

export async function beginLogin(input: { origin: string; redirectTo?: string }) {
  let origin: string;
  try {
    origin = new URL(input.origin).origin;
  } catch {
    throw new Error("Origem inválida.");
  }

  if (!isAllowedOrigin(origin)) {
    throw new Error(`Origem não autorizada para o fluxo OAuth: ${origin}`);
  }

  const redirectUri = `${origin}${AUTH_CALLBACK_PATH}`;
  const state = randomUrlSafeString(24);
  const nonce = randomUrlSafeString(24);
  const { verifier, challenge } = await createPkcePair();

  await saveFlowState({
    state,
    nonce,
    codeVerifier: verifier,
    redirectUri,
    redirectTo: sanitizeRedirectPath(input.redirectTo),
    createdAt: Date.now(),
  });

  const authorizationUrl = await buildAuthorizationUrl({
    redirectUri,
    state,
    codeChallenge: challenge,
    nonce,
  });

  return { authorizationUrl };
}

export async function finishLogin(input: { code: string; state: string }) {
  const flow = await consumeFlowState();
  if (!flow) {
    throw new Error("Sessão de login expirada. Inicie o acesso novamente.");
  }
  if (flow.state !== input.state) {
    throw new Error("Parâmetro `state` inválido — possível tentativa de CSRF.");
  }

  const tokens = await exchangeAuthorizationCode({
    code: input.code,
    redirectUri: flow.redirectUri,
    codeVerifier: flow.codeVerifier,
  });

  const identity = await resolveIdentity(tokens, flow.nonce);
  const mirrored = await mirrorAriiaIdentity(identity, tokens);

  return {
    tokenHash: mirrored.tokenHash,
    email: mirrored.email,
    redirectTo: flow.redirectTo,
  };
}