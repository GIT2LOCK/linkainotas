import { CloudCog } from "lucide-react";
import { SectionHeader } from "../components/SectionHeader";
import { callBackend } from "../services/backend";
import { useAsyncAction } from "../hooks/useAsyncAction";

export function CloudPage() {
  const action = useAsyncAction(() =>
    callBackend<{ status: string; space: string; folder: string; items: number }>("cloud.test"),
  );

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Dados"
        title="Armazenamento em nuvem"
        description="Verifique a disponibilidade do armazenamento e a origem dos documentos utilizados nos fluxos."
        actions={
          <button
            className="button primary"
            disabled={action.loading}
            onClick={() => action.run()}
            type="button"
          >
            Testar conexão
          </button>
        }
      />
      <div className="settings-grid">
        <div className="content-band">
          <CloudCog size={28} />
          <h3>Conexão de documentos</h3>
          <p>Valide a disponibilidade dos documentos armazenados para os fluxos do LinkAI.</p>
        </div>
        <div className="content-band">
          <h3>Status da conexão</h3>
          {action.data ? (
            <>
              <div className="activity-line">
                <span>Status</span>
                <strong>{action.data.status}</strong>
              </div>
              <div className="activity-line">
                <span>Espaço</span>
                <strong>{action.data.space}</strong>
              </div>
              <div className="activity-line">
                <span>Pasta</span>
                <strong>{action.data.folder || "/"}</strong>
              </div>
              <div className="activity-line">
                <span>Itens</span>
                <strong>{action.data.items}</strong>
              </div>
            </>
          ) : (
            <p>Use o teste para validar a conexão, a pasta e o acesso aos documentos.</p>
          )}
          {action.error ? <div className="alert danger">{action.error}</div> : null}
        </div>
      </div>
    </div>
  );
}
