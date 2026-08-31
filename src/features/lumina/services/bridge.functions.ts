import { createServerFn } from "@tanstack/react-start";

import type { CommandResult, UploadedDocumentsResponse } from "../types/backend";

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

interface BackendInvokeInput {
  action: string;
  payload: Record<string, unknown>;
}

interface UploadFilePayload {
  contentBase64: string;
  name: string;
  type: string | null;
}

interface UploadDocumentsInput {
  files: UploadFilePayload[];
}

interface PublishedService {
  missingMessage: string;
  token: string | null;
  url: string | null;
  urls: string[];
}

const LUMINA_ACTIONS = new Set(["lumina.start"]);
const PROCESSING_NOT_CONFIGURED =
  "Servico de processamento de documentos nao configurado. Defina LINKAI_PROCESSING_URL no ambiente publicado.";
const LUMINA_NOT_CONFIGURED =
  "Executor Lumina nao configurado. Defina LINKAI_LUMINA_URL no ambiente publicado.";
const QUICK_ACTION_TIMEOUT_MS = 5000;

export const invokePublishedBackend = createServerFn({ method: "POST" })
  .validator((data: unknown): BackendInvokeInput => {
    if (!data || typeof data !== "object") {
      throw new Error("Invalid backend payload.");
    }

    const candidate = data as Partial<BackendInvokeInput>;

    if (typeof candidate.action !== "string" || candidate.action.trim().length === 0) {
      throw new Error("Invalid backend action.");
    }

    return {
      action: candidate.action,
      payload:
        candidate.payload &&
        typeof candidate.payload === "object" &&
        !Array.isArray(candidate.payload)
          ? (candidate.payload as Record<string, unknown>)
          : {},
    };
  })
  .handler(async ({ data }): Promise<CommandResult<JsonValue>> => {
    const service = serviceForAction(data.action);

    if (!service.url) {
      return {
        ok: false,
        data: null,
        error: service.missingMessage,
      };
    }

    let lastError = "Nenhum executor disponivel no momento.";

    for (const url of service.urls) {
      try {
        const response = await fetchWithTimeout(`${url}/invoke`, {
          method: "POST",
          headers: jsonHeaders(service.token),
          body: JSON.stringify(data),
        }, data.action === "documents.process" ? undefined : QUICK_ACTION_TIMEOUT_MS);

        if (response.status === 409 || response.status === 503) {
          lastError = "Executor ocupado ou indisponivel.";
          continue;
        }

        if (!response.ok) {
          return {
            ok: false,
            data: null,
            error: `Servico respondeu com status ${response.status}.`,
          };
        }

        const result = normalizeBridgeResult((await response.json()) as CommandResult<JsonValue>);

        if (isBusyResult(result)) {
          lastError = "Executor ocupado ou indisponivel.";
          continue;
        }

        return result;
      } catch (error) {
        lastError =
          error instanceof Error ? error.message : "Nao foi possivel acionar o servico publicado.";
      }
    }

    return { ok: false, data: null, error: lastError };
  });

export const uploadPublishedDocuments = createServerFn({ method: "POST" })
  .validator((data: unknown): UploadDocumentsInput => {
    if (!data || typeof data !== "object") {
      throw new Error("Invalid upload payload.");
    }

    const files = (data as Partial<UploadDocumentsInput>).files;

    if (!Array.isArray(files) || files.length === 0) {
      throw new Error("Nenhum documento enviado.");
    }

    return {
      files: files.map((file) => {
        if (
          !file ||
          typeof file !== "object" ||
          typeof file.name !== "string" ||
          typeof file.contentBase64 !== "string"
        ) {
          throw new Error("Documento invalido.");
        }

        return {
          contentBase64: file.contentBase64,
          name: file.name,
          type: typeof file.type === "string" ? file.type : null,
        };
      }),
    };
  })
  .handler(async ({ data }): Promise<CommandResult<UploadedDocumentsResponse>> => {
    const service = processingService();

    if (!service.url) {
      return {
        ok: false,
        data: null,
        error: service.missingMessage,
      };
    }

    try {
      const formData = new FormData();

      for (const file of data.files) {
        const bytes = base64ToBytes(file.contentBase64);
        const blob = new Blob([bytes.buffer as ArrayBuffer], {
          type: file.type ?? "application/octet-stream",
        });
        formData.append("files", blob, file.name);
      }

      const response = await fetch(`${service.url}/uploads/documents`, {
        method: "POST",
        headers: tokenHeaders(service.token),
        body: formData,
      });

      if (!response.ok) {
        return {
          ok: false,
          data: null,
          error: `Servico de processamento respondeu com status ${response.status}.`,
        };
      }

      return {
        ok: true,
        data: (await response.json()) as UploadedDocumentsResponse,
        error: null,
      };
    } catch (error) {
      return {
        ok: false,
        data: null,
        error:
          error instanceof Error
            ? error.message
            : "Nao foi possivel enviar os documentos para processamento.",
      };
    }
  });

function serviceForAction(action: string): PublishedService {
  return LUMINA_ACTIONS.has(action) ? luminaService() : processingService();
}

function processingService(): PublishedService {
  const url =
    env("LINKAI_PROCESSING_URL") ??
    env("LINKAI_DOCUMENT_PROCESSING_URL") ??
    env("LINKAI_API_URL") ??
    env("LINKAI_BRIDGE_URL") ??
    env("VITE_LINKAI_API_URL");

  return {
    missingMessage: PROCESSING_NOT_CONFIGURED,
    token:
      env("LINKAI_PROCESSING_TOKEN") ??
      env("LINKAI_DOCUMENT_PROCESSING_TOKEN") ??
      env("LINKAI_BRIDGE_TOKEN"),
    url,
    urls: url ? [url] : [],
  };
}

function luminaService(): PublishedService {
  const urls = uniqueUrls([
    ...envList("LINKAI_LUMINA_URLS"),
    env("LINKAI_LUMINA_URL"),
    env("LINKAI_LUMINA_BRIDGE_URL"),
    env("LINKAI_BRIDGE_URL"),
  ]);

  return {
    missingMessage: LUMINA_NOT_CONFIGURED,
    token: env("LINKAI_LUMINA_TOKEN") ?? env("LINKAI_BRIDGE_TOKEN"),
    url: urls[0] ?? null,
    urls,
  };
}

function envList(name: string): string[] {
  return (process.env[name] ?? "")
    .split(",")
    .map((value) => value.trim().replace(/\/+$/, ""))
    .filter(Boolean);
}

function uniqueUrls(values: Array<string | null>): string[] {
  return [...new Set(values.filter((value): value is string => Boolean(value)))];
}

function isBusyResult(result: CommandResult<JsonValue>): boolean {
  if (!result.data || typeof result.data !== "object" || Array.isArray(result.data)) {
    return false;
  }

  return (result.data as { status?: unknown }).status === "busy";
}

async function fetchWithTimeout(
  input: string,
  init: RequestInit,
  timeoutMs: number | undefined,
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = timeoutMs === undefined
    ? undefined
    : setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId);
    }
  }
}

function env(name: string): string | null {
  const value = process.env[name]?.trim();
  return value ? value.replace(/\/+$/, "") : null;
}

function jsonHeaders(token: string | null): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...tokenHeaders(token),
  };
}

function tokenHeaders(token: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return bytes;
}

function normalizeBridgeResult(result: CommandResult<JsonValue>): CommandResult<JsonValue> {
  if (typeof result?.ok === "boolean") {
    return result;
  }

  return {
    ok: true,
    data: result as unknown as JsonValue,
    error: null,
  };
}
