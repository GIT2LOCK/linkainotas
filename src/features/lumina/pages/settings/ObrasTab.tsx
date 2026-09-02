import { useEffect, useState } from "react";
import { Building2, Plus, RefreshCw } from "lucide-react";

import { DataTable } from "../../components/DataTable";
import { useAsyncAction } from "../../hooks/useAsyncAction";
import { createObra, listObras, type ObraItem } from "../../services/access.functions";

const columns = [
  { key: "codigo", label: "Código" },
  { key: "nome", label: "Nome" },
  {
    key: "empresaNome",
    label: "Empresa",
    render: (row: Record<string, unknown>) =>
      String(row["empresaNome"] ?? `Empresa ${String(row["empresaId"] ?? "")}`),
  },
  {
    key: "tipo",
    label: "Tipo",
    render: (row: Record<string, unknown>) =>
      row["tipo"] === "escritorio" ? "ESCRITORIO" : "Obra",
  },
  {
    key: "status",
    label: "Status",
    render: (row: Record<string, unknown>) => (row["ativo"] === true ? "Ativa" : "Inativa"),
  },
];


export function ObrasTab({ canManage }: { canManage: boolean }) {
  const list = useAsyncAction(() => listObras());
  const [codigo, setCodigo] = useState("");
  const [nome, setNome] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const { run } = list;

  useEffect(() => {
    void run().catch(() => undefined);
  }, [run]);

  const obras: ObraItem[] = list.data ?? [];
  const escritorios = obras.filter((obra) => obra.tipo === "escritorio").length;

  async function submit() {
    setFeedback(null);
    setSaving(true);
    try {
      await createObra({ data: { codigo, nome } });
      setCodigo("");
      setNome("");
      setFeedback("Obra cadastrada.");
      await run();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="content-band">
        <Building2 aria-hidden="true" size={16} />
        <div>
          <h3>Obras da empresa</h3>
          <p>
            {escritorios > 1
              ? `Cada empresa tem o seu próprio ESCRITORIO — você vê ${escritorios} porque tem acesso a mais de uma empresa. Não são duplicados.`
              : escritorios === 1
                ? "O ESCRITORIO é criado automaticamente e não pode ser duplicado."
                : "Nenhum ESCRITORIO encontrado no seu escopo."}
          </p>
        </div>
      </div>


      {canManage ? (
        <div className="access-form">
          <label className="field">
            <span>Código</span>
            <input
              onChange={(event) => setCodigo(event.target.value.toUpperCase())}
              placeholder="OBRA-001"
              value={codigo}
            />
          </label>
          <label className="field">
            <span>Nome da obra</span>
            <input
              onChange={(event) => setNome(event.target.value)}
              placeholder="Residencial Alto da Serra"
              value={nome}
            />
          </label>
          <button
            className="button primary"
            disabled={saving || !codigo.trim() || !nome.trim()}
            onClick={() => void submit()}
            type="button"
          >
            <Plus aria-hidden="true" size={14} />
            Cadastrar obra
          </button>
        </div>
      ) : null}

      {feedback ? <p className="hint">{feedback}</p> : null}
      {list.error ? <p className="hint">{list.error}</p> : null}

      <div className="section-actions">
        <button
          className="button ghost"
          disabled={list.loading}
          onClick={() => void run().catch(() => undefined)}
          type="button"
        >
          <RefreshCw aria-hidden="true" size={14} />
          Atualizar
        </button>
      </div>

      <DataTable
        columns={columns}
        emptyLabel={list.loading ? "Carregando..." : "Nenhuma obra visível."}
        rows={obras as unknown as Record<string, unknown>[]}
      />
    </div>
  );
}
