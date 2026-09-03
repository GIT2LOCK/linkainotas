import { useEffect, useState, type FormEvent } from "react";
import { KeyRound, PlayCircle, X } from "lucide-react";
import { SectionHeader } from "../components/SectionHeader";
import {
  enqueueLuminaLaunch,
  getActiveLuminaRequest,
  getLuminaJobStatus,
  type LuminaJob,
} from "../services/lumina-queue.functions";
import {
  getMeuPerfil,
  saveMyInitialLuminaCredentials,
  type MeuPerfil,
} from "../services/profile.functions";

export function LaunchNotesPage() {
  const [job, setJob] = useState<LuminaJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(true);
  const [profile, setProfile] = useState<MeuPerfil | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [credentialDialogOpen, setCredentialDialogOpen] = useState(false);
  const [luminaUsername, setLuminaUsername] = useState("");
  const [luminaPassword, setLuminaPassword] = useState("");
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const jobId = job?.id;
  const jobStatus = job?.status;

  useEffect(() => {
    let cancelled = false;

    getActiveLuminaRequest({ data: {} })
      .then((activeJob) => {
        if (!cancelled && activeJob) setJob(activeJob);
      })
      .catch(() => {
        // The request can still be created normally if the optional restore fails.
      })
      .finally(() => {
        if (!cancelled) setRestoring(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    getMeuPerfil({ data: {} })
      .then((currentProfile) => {
        if (!cancelled) {
          setProfile(currentProfile);
          setLuminaUsername(currentProfile.luminaUsername ?? "");
        }
      })
      .catch(() => {
        // The server validates the profile again when credentials are saved.
      })
      .finally(() => {
        if (!cancelled) setProfileLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

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

  const enqueueRequest = async () => {
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

  const requestLaunch = () => {
    if (!profile?.luminaUsername || !profile.luminaPasswordSet) {
      setCredentialDialogOpen(true);
      setLuminaUsername(profile?.luminaUsername ?? "");
      setLuminaPassword("");
      return;
    }

    void enqueueRequest();
  };

  const saveCredentialsAndLaunch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSavingCredentials(true);
    setError(null);

    try {
      const saved = await saveMyInitialLuminaCredentials({
        data: { username: luminaUsername, password: luminaPassword },
      });
      setProfile((current) =>
        current
          ? {
              ...current,
              luminaUsername: saved.luminaUsername,
              luminaPasswordSet: saved.luminaPasswordSet,
              luminaCredentialsUpdatedAt: saved.luminaCredentialsUpdatedAt,
            }
          : current,
      );
      setLuminaPassword("");
      setCredentialDialogOpen(false);
      await enqueueRequest();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível salvar o login do Lumina.",
      );
    } finally {
      setSavingCredentials(false);
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
        ? `${queueLabel}Uma máquina disponível iniciou o atendimento. Ela permanecerá reservada enquanto o Lumina estiver aberto.`
        : job?.status === "succeeded"
          ? "Atendimento concluído e máquina liberada."
          : job?.status === "failed"
            ? (job.message ?? "Não foi possível concluir o atendimento.")
            : null;
  const progressMessage = job
    ? `Fila #${job.queueNumber} · ${job.completedItems}/${job.totalItems} item(ns) concluído(s)`
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
          disabled={loading || restoring || profileLoading || isActive}
          onClick={requestLaunch}
          type="button"
        >
          {restoring
            ? "Consultando fila"
            : profileLoading
              ? "Consultando perfil"
              : loading
                ? "Entrando na fila"
                : job?.status === "queued"
                  ? "Aguardando máquina"
                  : job?.status === "running"
                    ? "Em execução"
                    : "Iniciar lançamento"}
        </button>
        {progressMessage ? <p className="queue-progress">{progressMessage}</p> : null}
        {statusMessage ? (
          <div className={`alert ${statusClass}`} aria-live="polite">
            {statusMessage}
          </div>
        ) : null}
      </div>

      {credentialDialogOpen ? (
        <div className="modal-backdrop" role="presentation">
          <div
            aria-labelledby="lumina-credentials-title"
            aria-modal="true"
            className="modal-card"
            role="dialog"
          >
            <div className="modal-card-heading">
              <div className="modal-card-icon">
                <KeyRound aria-hidden="true" size={18} />
              </div>
              <div>
                <h2 id="lumina-credentials-title">Acesso do Lumina</h2>
                <p>Informe seu login para que uma máquina disponível faça o lançamento.</p>
              </div>
              <button
                aria-label="Fechar"
                className="icon-button"
                disabled={savingCredentials}
                onClick={() => setCredentialDialogOpen(false)}
                title="Fechar"
                type="button"
              >
                <X size={16} />
              </button>
            </div>
            <form className="modal-form" onSubmit={(event) => void saveCredentialsAndLaunch(event)}>
              <label className="field">
                <span>Usuário Lumina</span>
                <input
                  autoComplete="username"
                  autoFocus
                  onChange={(event) => setLuminaUsername(event.target.value)}
                  placeholder="Digite seu usuário"
                  required
                  value={luminaUsername}
                />
              </label>
              <label className="field">
                <span>Senha Lumina</span>
                <input
                  autoComplete="current-password"
                  onChange={(event) => setLuminaPassword(event.target.value)}
                  placeholder="Digite sua senha"
                  required
                  type="password"
                  value={luminaPassword}
                />
              </label>
              <p className="field-hint">
                A senha fica protegida e não é exibida novamente. Para trocar o login depois,
                solicite atendimento técnico no Meu Perfil.
              </p>
              <div className="modal-actions">
                <button
                  className="button ghost"
                  disabled={savingCredentials}
                  onClick={() => setCredentialDialogOpen(false)}
                  type="button"
                >
                  Cancelar
                </button>
                <button className="button primary" disabled={savingCredentials} type="submit">
                  <KeyRound aria-hidden="true" size={14} />
                  {savingCredentials ? "Salvando..." : "Salvar e iniciar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
