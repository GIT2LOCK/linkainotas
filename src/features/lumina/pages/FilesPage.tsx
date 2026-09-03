import { RefreshCw } from "lucide-react";
import { useEffect } from "react";
import { DataTable } from "../components/DataTable";
import { SectionHeader } from "../components/SectionHeader";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { callBackend } from "../services/backend";
import type { LocalFileInfo } from "../types/backend";

const columns = [
  { key: "name", label: "Nome" },
  { key: "documentType", label: "Documento" },
  { key: "pageCount", label: "Páginas" },
  {
    key: "sizeBytes",
    label: "Tamanho",
    render: (row: Record<string, unknown>) => formatBytes(row["sizeBytes"] as number | null),
  },
  { key: "status", label: "Status" },
  {
    key: "source",
    label: "Origem",
    render: (row: Record<string, unknown>) => displayOrigin(String(row["source"] ?? "-")),
  },
  {
    key: "hash",
    label: "Hash",
    render: (row: Record<string, unknown>) =>
      typeof row["hash"] === "string" ? row["hash"].slice(0, 12) : "-",
  },
  { key: "parser", label: "Parser" },
  {
    key: "processedAt",
    label: "Processado em",
    render: (row: Record<string, unknown>) => formatDate(row["processedAt"] as string | null),
  },
  {
    key: "path",
    label: "Local",
    render: (row: Record<string, unknown>) => String(row["path"] ?? "-"),
  },
  {
    key: "error",
    label: "Erro",
    render: (row: Record<string, unknown>) => String(row["error"] ?? "-"),
  },
];

export function FilesPage() {
  const action = useAsyncAction(() => callBackend<LocalFileInfo[]>("files.list"));
  const { run } = action;

  useEffect(() => {
    run().catch(() => undefined);
  }, [run]);

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Dados"
        title="Arquivos processados"
        description="Consulte o catálogo de documentos processados e seus respectivos resultados."
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
        emptyLabel="Nenhum PDF registrado ainda."
        rows={(action.data ?? []) as unknown as Record<string, unknown>[]}
      />
    </div>
  );
}

function formatBytes(value: number | null) {
  if (!value) {
    return "-";
  }

  const units = ["B", "KB", "MB", "GB"];
  const index = Math.floor(Math.log(value) / Math.log(1024));
  return `${(value / 1024 ** index).toFixed(1)} ${units[index]}`;
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

function displayOrigin(source: string) {
  return source === "supabase" || source === "fallback" ? "Nuvem" : source;
}
