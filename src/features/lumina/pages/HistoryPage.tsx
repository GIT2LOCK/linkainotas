import { RefreshCw } from "lucide-react";
import { useEffect } from "react";
import { DataTable } from "../components/DataTable";
import { SectionHeader } from "../components/SectionHeader";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { callBackend } from "../services/backend";
import type { ProcessingHistoryItem } from "../types/backend";

const columns = [
  {
    key: "processedAt",
    label: "Data",
    render: (row: Record<string, unknown>) => formatDate(row["processedAt"] as string | null),
  },
  {
    key: "source",
    label: "Origem",
    render: (row: Record<string, unknown>) => displayOrigin(String(row["source"] ?? "-")),
  },
  { key: "listed", label: "Listados" },
  { key: "processed", label: "Processados" },
  { key: "duplicated", label: "Duplicados" },
  { key: "failed", label: "Erros" },
  {
    key: "elapsedSeconds",
    label: "Tempo",
    render: (row: Record<string, unknown>) => formatSeconds(Number(row["elapsedSeconds"] ?? 0)),
  },
  { key: "status", label: "Status" },
  {
    key: "downloadPath",
    label: "Download",
    render: (row: Record<string, unknown>) => String(row["downloadPath"] ?? "-"),
  },
];

export function HistoryPage() {
  const action = useAsyncAction(() => callBackend<ProcessingHistoryItem[]>("history.list"));
  const { run } = action;

  useEffect(() => {
    run().catch(() => undefined);
  }, [run]);

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Sistema"
        title="Histórico"
        description="Processamentos, origem, duração, erros e arquivos gerados."
        actions={
          <button
            className="button secondary"
            disabled={action.loading}
            onClick={() => action.run()}
            type="button"
          >
            <RefreshCw size={16} />
            Atualizar
          </button>
        }
      />

      {action.error ? <div className="alert danger">{action.error}</div> : null}

      <DataTable
        columns={columns}
        emptyLabel="Sem execuções registradas para exibição."
        rows={(action.data ?? []) as unknown as Record<string, unknown>[]}
      />
    </div>
  );
}

function formatDate(value: string | null) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function formatSeconds(value: number) {
  if (!value) {
    return "-";
  }

  return `${value.toFixed(2)}s`;
}

function displayOrigin(source: string) {
  return source === "supabase" || source === "fallback" ? "Nuvem" : source;
}
