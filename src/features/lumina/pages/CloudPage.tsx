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
        title="Nuvem"
        description="Verifique a conexão privada, o espaço de arquivos e a pasta configurada."
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
          <h3>Conexão privada</h3>
          <p>Use este painel para validar se os documentos estão acessíveis na nuvem.</p>
        </div>
        <div className="content-band">
          <h3>Status</h3>
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
