import type { CommandResult, UploadedDocumentsResponse } from "../types/backend";

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

export async function callBackend<T>(action: string, payload: object = {}): Promise<T> {
  const result = await callLocalApi<T>(action, payload);

  if (!result.ok) {
    throw new Error(result.error ?? "Backend command failed");
  }

  return result.data as T;
}

export function isTauriRuntime(): boolean {
  return false;
}

export async function uploadLocalDocuments(files: File[]): Promise<UploadedDocumentsResponse> {
  const formData = new FormData();

  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(`${localApiBaseUrl()}/uploads/documents`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Local upload unavailable: ${response.status}`);
  }

  return (await response.json()) as UploadedDocumentsResponse;
}

export const uploadLocalPdfs = uploadLocalDocuments;

async function callLocalApi<T>(action: string, payload: object): Promise<CommandResult<T>> {
  const response = await fetch(`${localApiBaseUrl()}/invoke`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ action, payload }),
  });

  if (!response.ok) {
    throw new Error(`Local API unavailable: ${response.status}`);
  }

  return (await response.json()) as CommandResult<T>;
}

function localApiBaseUrl(): string {
  const configuredUrl = import.meta.env.VITE_LINKAI_API_URL;
  if (configuredUrl) {
    return configuredUrl;
  }

  if (typeof window !== "undefined" && window.location.hostname) {
    return `${window.location.protocol}//${window.location.hostname}:8765`;
  }

  return "http://127.0.0.1:8765";
}
