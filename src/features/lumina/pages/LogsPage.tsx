import { useEffect } from "react";
import { SectionHeader } from "../components/SectionHeader";
import { callBackend } from "../services/backend";
import { useAsyncAction } from "../hooks/useAsyncAction";

interface LogsResponse {
  path: string;
  lines: string[];
}

export function LogsPage() {
  const action = useAsyncAction(() => callBackend<LogsResponse>("logs.latest", { lines: 500 }));
  const { run } = action;

  useEffect(() => {
    run().catch(() => undefined);
  }, [run]);

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Sistema"
        title="Logs"
        description="Acompanhe os eventos recentes do sistema."
        actions={
          <button className="button secondary" onClick={() => action.run()} type="button">
            Atualizar
          </button>
        }
      />
      {action.error ? <div className="alert danger">{action.error}</div> : null}
      <pre className="log-viewer">
        {(action.data?.lines ?? ["Sem logs disponíveis."]).join("\n")}
      </pre>
    </div>
  );
}
