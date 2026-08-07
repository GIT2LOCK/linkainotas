/** Identidade vinda do Ariia (fonte de verdade dos usuários). */
export type AriiaIdentity = {
  /** ID numérico do usuário no Ariia, em texto. */
  sub: string;
  email: string;
  name: string | null;
  picture: string | null;
  permissao: string | null;
};

export type AriiaSessionToken = {
  token: string;
  /** Epoch em segundos. */
  expiresAt: number | null;
};