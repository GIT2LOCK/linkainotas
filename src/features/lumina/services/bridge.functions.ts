import { createServerFn } from "@tanstack/react-start";

import type { CommandResult } from "../types/backend";

interface BridgeInvokeInput {
  action: string;
  payload: Record<string, unknown>;
}

const BRIDGE_NOT_CONFIGURED =
  "Executor Lumina nao configurado. Defina LINKAI_BRIDGE_URL no ambiente publicado.";

export const invokeLuminaBridge = createServerFn({ method: "POST" })
  .validator((data: unknown): BridgeInvokeInput => {
    if (!data || typeof data !== "object") {
      throw new Error("Invalid bridge payload.");
    }

    const candidate = data as Partial<BridgeInvokeInput>;

    if (typeof candidate.action !== "string" || candidate.action.trim().length === 0) {
      throw new Error("Invalid bridge action.");
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
  .handler(async ({ data }): Promise<CommandResult<unknown>> => {
    const bridgeUrl = bridgeBaseUrl();

    if (!bridgeUrl) {
      return {
        ok: false,
        data: null,
        error: BRIDGE_NOT_CONFIGURED,
      };
    }

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      const token = process.env["LINKAI_BRIDGE_TOKEN"];

      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      const response = await fetch(`${bridgeUrl}/invoke`, {
        method: "POST",
        headers,
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        return {
          ok: false,
          data: null,
          error: `Executor Lumina respondeu com status ${response.status}.`,
        };
      }

      const result = (await response.json()) as CommandResult<unknown>;
      return normalizeBridgeResult(result);
    } catch (error) {
      return {
        ok: false,
        data: null,
        error:
          error instanceof Error ? error.message : "Nao foi possivel acionar o executor Lumina.",
      };
    }
  });

function bridgeBaseUrl(): string | null {
  const configuredUrl =
    process.env["LINKAI_BRIDGE_URL"] ??
    process.env["LINKAI_API_URL"] ??
    process.env["VITE_LINKAI_API_URL"];

  if (!configuredUrl) {
    return null;
  }

  return configuredUrl.trim().replace(/\/+$/, "");
}

function normalizeBridgeResult(result: CommandResult<unknown>): CommandResult<unknown> {
  if (typeof result?.ok === "boolean") {
    return result;
  }

  return {
    ok: true,
    data: result,
    error: null,
  };
}
