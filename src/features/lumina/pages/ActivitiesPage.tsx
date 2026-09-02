import { useEffect } from "react";
import { RefreshCw } from "lucide-react";

import { DataTable } from "../components/DataTable";
import { SectionHeader } from "../components/SectionHeader";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { listAtividades, type AtividadeItem } from "../services/access.functions";

const columns = [
  { key: "quando", label: "Data e hora" },
  { key: "usuario", label: "Usuário" },
  { key: "email", label: "E-mail" },
  { key: "obra", label: "Obra" },
  { key: "acao", label: "Operação" },
  { key: "arquivos", label: "Arquivos" },
  { key: "status", label: "Status" },
  { key: "mensagem", label: "Mensagem" },
];

export function ActivitiesPage() {
  const action = useAsyncAction(() => listAtividades());
  const { run } = action;

  useEffect(() => {
    void run().catch(() => undefined);
    const timer = window.setInterval(() => {
      void run().catch(() => undefined);
    }, 15_000);
    return () => window.clearInterval(timer);
  }, [run]);

  const rows = (action.data ?? []).map((row: AtividadeItem) => ({
    quando: formatDate(row.createdAt),
    usuario: row.usuario ?? "-",
    email: row.email ?? "-",
    obra: row.obra ?? "-",
    acao: row.acao,
    arquivos: row.arquivos ?? "-",
    status: row.status,
    mensagem: row.mensagem ?? "-",
  }));

  return (
    <div className="page-stack">
      <SectionHeader
        actions={
          <button
            className="button ghost"
            disabled={action.loading}
            onClick={() => void run().catch(() => undefined)}
            type="button"
          >
            <RefreshCw aria-hidden="true" size={14} />
            Atualizar
          </button>
        }
        description="Operações registradas nas obras visíveis para você, atualizadas automaticamente."
        eyebrow="Sistema"
        title="Atividades"
      />
      {action.error ? <p className="hint">{action.error}</p> : null}
      <DataTable
        columns={columns}
        emptyLabel={action.loading ? "Carregando..." : "Nenhuma atividade registrada."}
        rows={rows}
      />
    </div>
  );
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("pt-BR");
}
