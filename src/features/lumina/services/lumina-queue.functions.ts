import { createServerFn } from "@tanstack/react-start";

import { requireLinkaiUser } from "@/lib/auth/require-user";
import type { Database } from "@/integrations/supabase/types";

export type LuminaJobStatus = "queued" | "running" | "succeeded" | "failed" | "canceled";

export type LuminaJob = {
  id: string;
  queueNumber: number | null;
  status: LuminaJobStatus;
  message: string | null;
  workerId: string | null;
  totalItems: number;
  completedItems: number;
  failedItems: number;
  canceledItems: number;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
};

type RequestRow = Database["public"]["Tables"]["lumina_queue_requests"]["Row"];

const REQUEST_COLUMNS =
  "id, queue_number, status, message, total_items, completed_items, failed_items, canceled_items, created_at, started_at, finished_at";

type RequestSelection = Pick<
  RequestRow,
  | "id"
  | "queue_number"
  | "status"
  | "message"
  | "total_items"
  | "completed_items"
  | "failed_items"
  | "canceled_items"
  | "created_at"
  | "started_at"
  | "finished_at"
>;

function mapRequest(row: RequestSelection, workerId: string | null = null): LuminaJob {
  return {
    id: row.id,
    queueNumber: row.queue_number === null ? null : Number(row.queue_number),
    status: row.status as LuminaJobStatus,
    message: row.message,
    workerId,
    totalItems: row.total_items,
    completedItems: row.completed_items,
    failedItems: row.failed_items,
    canceledItems: row.canceled_items,
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
    const { data, error } = await context.supabase.rpc("enqueue_lumina_request", {
      p_action: "launch_notes",
      p_payload: {},
      p_items: [],
    });

    if (error) throw error;

    const row = (Array.isArray(data) ? data[0] : data) as RequestSelection | null;
    if (!row) throw new Error("Não foi possível criar a solicitação na fila.");
    return mapRequest(row);
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
      .from("lumina_queue_requests")
      .select(REQUEST_COLUMNS)
      .eq("id", data.id)
      .single();

    if (error) throw error;

    const { data: items } = await context.supabase
      .from("lumina_jobs")
      .select("worker_id, message, status")
      .eq("queue_request_id", data.id)
      .eq("status", "running")
      .limit(1);

    const runningItem = items?.[0] ?? null;
    return mapRequest(row, runningItem?.worker_id ?? null);
  });

export const getActiveLuminaRequest = createServerFn({ method: "POST" })
  .middleware([requireLinkaiUser])
  .validator((data: unknown) => {
    if (data !== undefined && (typeof data !== "object" || data === null || Array.isArray(data))) {
      throw new Error("Invalid queue payload.");
    }
    return {};
  })
  .handler(async ({ context }): Promise<LuminaJob | null> => {
    const { data: rows, error } = await context.supabase
      .from("lumina_queue_requests")
      .select(REQUEST_COLUMNS)
      .in("status", ["queued", "running"])
      .order("created_at", { ascending: false })
      .limit(1);

    if (error) throw error;

    const row = (rows?.[0] ?? null) as RequestSelection | null;
    if (!row) return null;

    const { data: items } = await context.supabase
      .from("lumina_jobs")
      .select("worker_id, message, status")
      .eq("queue_request_id", row.id)
      .eq("status", "running")
      .limit(1);

    return mapRequest(row, items?.[0]?.worker_id ?? null);
  });
