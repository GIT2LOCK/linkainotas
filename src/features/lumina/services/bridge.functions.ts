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
}

const LUMINA_ACTIONS = new Set(["lumina.start"]);
const PROCESSING_NOT_CONFIGURED =
  "Servico de processamento de documentos nao configurado. Defina LINKAI_PROCESSING_URL no ambiente publicado.";
const LUMINA_NOT_CONFIGURED =
  "Executor Lumina nao configurado. Defina LINKAI_LUMINA_URL no ambiente publicado.";

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

    try {
      const response = await fetch(`${service.url}/invoke`, {
        method: "POST",
        headers: jsonHeaders(service.token),
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        return {
          ok: false,
          data: null,
          error: `Servico respondeu com status ${response.status}.`,
        };
      }

      const result = (await response.json()) as CommandResult<JsonValue>;
      return normalizeBridgeResult(result);
    } catch (error) {
      return {
        ok: false,
        data: null,
        error:
          error instanceof Error ? error.message : "Nao foi possivel acionar o servico publicado.",
      };
    }
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
  return {
    missingMessage: PROCESSING_NOT_CONFIGURED,
    token:
      env("LINKAI_PROCESSING_TOKEN") ??
      env("LINKAI_DOCUMENT_PROCESSING_TOKEN") ??
      env("LINKAI_BRIDGE_TOKEN"),
    url:
      env("LINKAI_PROCESSING_URL") ??
      env("LINKAI_DOCUMENT_PROCESSING_URL") ??
      env("LINKAI_API_URL") ??
      env("LINKAI_BRIDGE_URL") ??
      env("VITE_LINKAI_API_URL"),
  };
}

function luminaService(): PublishedService {
  return {
    missingMessage: LUMINA_NOT_CONFIGURED,
    token: env("LINKAI_LUMINA_TOKEN") ?? env("LINKAI_BRIDGE_TOKEN"),
    url: env("LINKAI_LUMINA_URL") ?? env("LINKAI_LUMINA_BRIDGE_URL") ?? env("LINKAI_BRIDGE_URL"),
  };
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
    data: result,
    error: null,
  };
}
