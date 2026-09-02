import { useEffect, useMemo, useState } from "react";
import { RefreshCw, UserPlus } from "lucide-react";

import { DataTable } from "../../components/DataTable";
import { useAsyncAction } from "../../hooks/useAsyncAction";
import {
  assignUsuario,
  createConvite,
  listConvites,
  listObras,
  listUsuarios,
  type ConviteItem,
  type ObraItem,
  type PerfilItem,
  type UsuarioItem,
} from "../../services/access.functions";

const TWO_FACTOR_LABEL: Record<string, string> = {
  required: "Obrigatório",
  optional: "Opcional",
  disabled: "Desativado",
};

export function UsuariosTab({ perfis }: { perfis: PerfilItem[] }) {
  const usuarios = useAsyncAction(() => listUsuarios());
  const convites = useAsyncAction(() => listConvites());
  const obras = useAsyncAction(() => listObras());

  const [mode, setMode] = useState<"convite" | "atribuir">("convite");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [usuarioId, setUsuarioId] = useState("");
  const [obraId, setObraId] = useState("");
  const [perfilCodigo, setPerfilCodigo] = useState("");
  const [twoFactorPolicy, setTwoFactorPolicy] = useState("required");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const reload = usuarios.run;
  const reloadConvites = convites.run;
  const reloadObras = obras.run;

  useEffect(() => {
    void reload().catch(() => undefined);
    void reloadConvites().catch(() => undefined);
    void reloadObras().catch(() => undefined);
  }, [reload, reloadConvites, reloadObras]);

  const obraList: ObraItem[] = obras.data ?? [];
  const perfisAtribuiveis = useMemo(
    () => perfis.filter((perfil) => perfil.codigo !== "superadmin_2lock"),
    [perfis],
  );

  const perfilSelecionado = perfisAtribuiveis.find((perfil) => perfil.codigo === perfilCodigo);
  const obrasPermitidas =
    perfilSelecionado?.codigo === "supervisor_empresa"
      ? obraList.filter((obra) => obra.tipo === "escritorio")
      : obraList;

  const usuarioRows = (usuarios.data ?? []).map((row: UsuarioItem) => ({
    nome: row.nome,
    email: row.email,
    status: row.ativo ? "Ativo" : "Inativo",
    obra: row.obraNome ?? "-",
    funcao: perfilLabel(perfis, row.perfilCodigo),
    doisFatores: TWO_FACTOR_LABEL[row.twoFactorPolicy] ?? row.twoFactorPolicy,
  }));

  const conviteRows = (convites.data ?? [])
    .filter((row: ConviteItem) => row.status === "pending")
    .map((row) => ({
      nome: row.nome,
      email: row.email,
      obra: row.obraNome ?? "-",
      funcao: perfilLabel(perfis, row.perfilCodigo),
      doisFatores: TWO_FACTOR_LABEL[row.twoFactorPolicy] ?? row.twoFactorPolicy,
      status: "Pendente",
    }));

  async function submit() {
    setFeedback(null);
    setSaving(true);
    try {
      if (mode === "convite") {
        await createConvite({ data: { nome, email, obraId, perfilCodigo, twoFactorPolicy } });
        setNome("");
        setEmail("");
        setFeedback("Pré-cadastro criado. O acesso será liberado no primeiro login.");
      } else {
        await assignUsuario({
          data: { usuarioId: Number(usuarioId), obraId, perfilCodigo, principal: true },
        });
        setFeedback("Usuário atribuído à obra.");
      }
      await Promise.all([reload(), reloadConvites()]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  }

  const formValid =
    obraId &&
    perfilCodigo &&
    (mode === "convite" ? nome.trim() && email.trim() && twoFactorPolicy : usuarioId);

  return (
    <div className="page-stack">
      <div className="access-tabs">
        <button
          className={`segmented ${mode === "convite" ? "is-active" : ""}`}
          onClick={() => setMode("convite")}
          type="button"
        >
          Pré-cadastrar usuário
        </button>
        <button
          className={`segmented ${mode === "atribuir" ? "is-active" : ""}`}
          onClick={() => setMode("atribuir")}
          type="button"
        >
          Atribuir usuário existente
        </button>
      </div>

      <div className="access-form">
        {mode === "convite" ? (
          <>
            <label className="field">
              <span>Nome</span>
              <input onChange={(event) => setNome(event.target.value)} value={nome} />
            </label>
            <label className="field">
              <span>E-mail</span>
              <input
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                value={email}
              />
            </label>
          </>
        ) : (
          <label className="field">
            <span>Usuário</span>
            <select onChange={(event) => setUsuarioId(event.target.value)} value={usuarioId}>
              <option value="">Selecione</option>
              {(usuarios.data ?? []).map((row) => (
                <option key={row.id} value={String(row.id)}>
                  {row.nome} — {row.email}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="field">
          <span>Função</span>
          <select
            onChange={(event) => {
              setPerfilCodigo(event.target.value);
              setObraId("");
            }}
            value={perfilCodigo}
          >
            <option value="">Selecione</option>
            {perfisAtribuiveis.map((perfil) => (
              <option key={perfil.codigo} value={perfil.codigo}>
                {perfil.nome}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Obra</span>
          <select onChange={(event) => setObraId(event.target.value)} value={obraId}>
            <option value="">Selecione</option>
            {obrasPermitidas.map((obra) => (
              <option key={obra.id} value={obra.id}>
                {obra.tipo === "escritorio" ? "ESCRITORIO" : obra.nome}
              </option>
            ))}
          </select>
        </label>

        {mode === "convite" ? (
          <label className="field">
            <span>Autenticação em duas etapas</span>
            <select
              onChange={(event) => setTwoFactorPolicy(event.target.value)}
              value={twoFactorPolicy}
            >
              <option value="required">Obrigatória</option>
              <option value="optional">Opcional</option>
              <option value="disabled">Desativada</option>
            </select>
          </label>
        ) : null}

        <button
          className="button primary"
          disabled={saving || !formValid}
          onClick={() => void submit()}
          type="button"
        >
          <UserPlus aria-hidden="true" size={14} />
          {mode === "convite" ? "Pré-cadastrar" : "Atribuir"}
        </button>
      </div>

      <p className="hint">Nenhuma senha é armazenada pelo LinkAI.</p>
      {feedback ? <p className="hint">{feedback}</p> : null}
      {usuarios.error ? <p className="hint">{usuarios.error}</p> : null}

      <div className="section-actions">
        <button
          className="button ghost"
          disabled={usuarios.loading}
          onClick={() => {
            void reload().catch(() => undefined);
            void reloadConvites().catch(() => undefined);
          }}
          type="button"
        >
          <RefreshCw aria-hidden="true" size={14} />
          Atualizar
        </button>
      </div>

      <DataTable
        columns={[
          { key: "nome", label: "Nome" },
          { key: "email", label: "E-mail" },
          { key: "status", label: "Status" },
          { key: "obra", label: "Obra" },
          { key: "funcao", label: "Função" },
          { key: "doisFatores", label: "2FA" },
        ]}
        emptyLabel={usuarios.loading ? "Carregando..." : "Nenhum usuário na sua empresa."}
        rows={usuarioRows}
      />

      <div className="content-band">
        <div>
          <h3>Convites pendentes</h3>
          <p>Vínculo de empresa, obra e função aplicado no primeiro acesso.</p>
        </div>
      </div>

      <DataTable
        columns={[
          { key: "nome", label: "Nome" },
          { key: "email", label: "E-mail" },
          { key: "obra", label: "Obra" },
          { key: "funcao", label: "Função" },
          { key: "doisFatores", label: "2FA" },
          { key: "status", label: "Status" },
        ]}
        emptyLabel="Nenhum convite pendente."
        rows={conviteRows}
      />
    </div>
  );
}

function perfilLabel(perfis: PerfilItem[], codigo: string | null): string {
  if (!codigo) return "-";
  return perfis.find((perfil) => perfil.codigo === codigo)?.nome ?? codigo;
}
