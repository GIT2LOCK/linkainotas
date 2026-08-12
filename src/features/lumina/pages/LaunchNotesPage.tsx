import { PlayCircle } from "lucide-react";
import { SectionHeader } from "../components/SectionHeader";
import { callBackend } from "../services/backend";
import { useAsyncAction } from "../hooks/useAsyncAction";

export function LaunchNotesPage() {
  const action = useAsyncAction(() =>
    callBackend<{ status: string; message: string }>("lumina.start"),
  );

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Operação"
        title="Lançar Notas"
        description="Inicie o fluxo de lançamento no Lumina sob demanda."
      />
      <div className="launch-panel">
        <PlayCircle size={44} />
        <h2>Automação Lumina</h2>
        <p>Abra o Lumina e acompanhe a execução do lançamento.</p>
        <button
          className="button primary"
          disabled={action.loading}
          onClick={() => action.run()}
          type="button"
        >
          {action.loading ? "Iniciando" : "Iniciar lançamento"}
        </button>
        {action.data ? <div className="alert success">{action.data.message}</div> : null}
        {action.error ? <div className="alert danger">{action.error}</div> : null}
      </div>
    </div>
  );
}
