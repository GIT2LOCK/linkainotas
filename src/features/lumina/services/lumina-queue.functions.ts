import { createServerFn } from "@tanstack/react-start";

import { requireLinkaiUser } from "@/lib/auth/require-user";
import type { Database } from "@/integrations/supabase/types";

export type LuminaJobStatus = "queued" | "running" | "succeeded" | "failed" | "canceled";

export type LuminaJob = {
  id: string;
  status: LuminaJobStatus;
  message: string | null;
  workerId: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
};

type LuminaJobRow = Database["public"]["Tables"]["lumina_jobs"]["Row"];

const JOB_COLUMNS = "id, status, message, worker_id, created_at, started_at, finished_at";

function mapJob(
  row: Pick<
    LuminaJobRow,
    "id" | "status" | "message" | "worker_id" | "created_at" | "started_at" | "finished_at"
  >,
): LuminaJob {
  return {
    id: row.id,
    status: row.status as LuminaJobStatus,
    message: row.message,
    workerId: row.worker_id,
    createdAt: row.created_at,
    startedAt: row.started_at,
    finishedAt: row.finished_at,
  };
}

export const enqueueLuminaLaunch = createServerFn({ method: "POST" })
  .middleware([requireLinkaiUser])
  .validator((data: unknown) => {
    if (data !== undefined && (typeof data !== "object" || data === null || Array.isArray(data))) {
      throw new Error("Invalid queue payload.");
    }
    return {};
  })
  .handler(async ({ context }) => {
    const { data, error } = await context.supabase
      .from("lumina_jobs")
      .insert({
        requested_by: context.authUserId,
        empresa_id: context.user.empresaId,
        action: "launch_notes",
        payload: {},
      })
      .select(JOB_COLUMNS)
      .single();

    if (error) throw error;
    return mapJob(data);
  });

export const getLuminaJobStatus = createServerFn({ method: "POST" })
  .middleware([requireLinkaiUser])
  .validator((data: unknown) => {
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      throw new Error("Invalid queue job.");
    }

    const id = (data as { id?: unknown }).id;
    if (typeof id !== "string" || id.trim().length === 0) {
      throw new Error("Invalid queue job id.");
    }

    return { id };
  })
  .handler(async ({ data, context }) => {
    const { data: row, error } = await context.supabase
      .from("lumina_jobs")
      .select(JOB_COLUMNS)
      .eq("id", data.id)
      .single();

    if (error) throw error;
    return mapJob(row);
  });
