function toBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

/** Encrypts Lumina secrets on the LinkAI server before they reach Supabase. */
export async function encryptLuminaSecret(value: string, secret: string): Promise<string> {
  const webCrypto = globalThis.crypto;
  const encoder = new TextEncoder();
  const keyDigest = await webCrypto.subtle.digest("SHA-256", encoder.encode(secret));
  const key = await webCrypto.subtle.importKey("raw", keyDigest, { name: "AES-GCM" }, false, [
    "encrypt",
  ]);
  const iv = webCrypto.getRandomValues(new Uint8Array(12));
  const encryptedWithTag = new Uint8Array(
    await webCrypto.subtle.encrypt({ name: "AES-GCM", iv }, key, encoder.encode(value)),
  );
  const tag = encryptedWithTag.slice(-16);
  const encrypted = encryptedWithTag.slice(0, -16);

  return ["v1", toBase64Url(iv), toBase64Url(tag), toBase64Url(encrypted)].join(":");
}
