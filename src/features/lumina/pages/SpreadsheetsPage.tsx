import { useEffect } from "react";
import { DataTable } from "../components/DataTable";
import { SectionHeader } from "../components/SectionHeader";
import { callBackend } from "../services/backend";
import type { SpreadsheetInfo } from "../types/backend";
import { useAsyncAction } from "../hooks/useAsyncAction";

const columns = [
  { key: "name", label: "Nome" },
  {
    key: "sizeBytes",
    label: "Tamanho",
    render: (row: Record<string, unknown>) => `${((row.sizeBytes as number) / 1024).toFixed(1)} KB`,
  },
  {
    key: "modifiedAt",
    label: "Modificado",
    render: (row: Record<string, unknown>) =>
      new Date((row.modifiedAt as number) * 1000).toLocaleString(),
  },
  { key: "path", label: "Caminho" },
];

export function SpreadsheetsPage() {
  const action = useAsyncAction(() => callBackend<SpreadsheetInfo[]>("spreadsheets.list"));
  const { run } = action;

  useEffect(() => {
    run().catch(() => undefined);
  }, [run]);

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Dados"
        title="Planilhas"
        description="Consulte os arquivos Excel gerados."
        actions={
          <button className="button secondary" onClick={() => action.run()} type="button">
            Atualizar
          </button>
        }
      />
      {action.error ? <div className="alert danger">{action.error}</div> : null}
      <DataTable
        columns={columns}
        emptyLabel="Nenhuma planilha gerada."
        rows={(action.data ?? []) as unknown as Record<string, unknown>[]}
      />
    </div>
  );
}
