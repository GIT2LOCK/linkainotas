import { useEffect, useState } from "react";
import { PlayCircle } from "lucide-react";
import { SectionHeader } from "../components/SectionHeader";
import {
  enqueueLuminaLaunch,
  getLuminaJobStatus,
  type LuminaJob,
} from "../services/lumina-queue.functions";

export function LaunchNotesPage() {
  const [job, setJob] = useState<LuminaJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const jobId = job?.id;
  const jobStatus = job?.status;

  useEffect(() => {
    if (!jobId || !["queued", "running"].includes(jobStatus ?? "")) return;

    let cancelled = false;
    const poll = async () => {
      try {
        const nextJob = await getLuminaJobStatus({ data: { id: jobId } });
        if (!cancelled) {
          setJob(nextJob);
          setError(null);
        }
      } catch (pollError) {
        if (!cancelled) {
          setError(
            pollError instanceof Error ? pollError.message : "Não foi possível consultar a fila.",
          );
        }
      }
    };

    const interval = window.setInterval(poll, 3000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [jobId, jobStatus]);

  const requestLaunch = async () => {
    setLoading(true);
    setError(null);

    try {
      setJob(await enqueueLuminaLaunch({ data: {} }));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível entrar na fila de lançamento.",
      );
    } finally {
      setLoading(false);
    }
  };

  const isActive = job?.status === "queued" || job?.status === "running";
  const statusClass =
    job?.status === "failed" || error
      ? "danger"
      : job?.status === "succeeded"
        ? "success"
        : "warning";
  const queueLabel = job?.queueNumber ? `Solicitação nº ${job.queueNumber}. ` : "";
  const statusMessage = error
    ? error
    : job?.status === "queued"
      ? `${queueLabel}Pedido colocado na fila. Aguardando uma máquina disponível.`
      : job?.status === "running"
        ? "Uma máquina disponível iniciou o atendimento. Ela permanecerá reservada enquanto o Lumina estiver aberto."
        : job?.status === "succeeded"
          ? "Atendimento concluído e máquina liberada."
          : job?.status === "failed"
            ? (job.message ?? "Não foi possível concluir o atendimento.")
            : null;

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
          disabled={loading || isActive}
          onClick={requestLaunch}
          type="button"
        >
          {loading
            ? "Entrando na fila"
            : job?.status === "queued"
              ? "Aguardando máquina"
              : job?.status === "running"
                ? "Em execução"
                : "Iniciar lançamento"}
        </button>
        {statusMessage ? (
          <div className={`alert ${statusClass}`} aria-live="polite">
            {statusMessage}
          </div>
        ) : null}
      </div>
    </div>
  );
}
