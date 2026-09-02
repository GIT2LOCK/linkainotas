import { useEffect, useMemo, useState } from "react";
import { Check, Pencil, RefreshCw, ShieldCheck, UserPlus, X } from "lucide-react";

import { DataTable } from "../../components/DataTable";
import { useAsyncAction } from "../../hooks/useAsyncAction";
import {
  createConvite,
  listConvites,
  listObras,
  listUsuarios,
  updateUsuarioAcessos,
  type ConviteItem,
  type ObraItem,
  type PerfilItem,
  type PermissaoItem,
  type UsuarioItem,
} from "../../services/access.functions";

const TWO_FACTOR_LABEL: Record<string, string> = {
  required: "Obrigatório",
  optional: "Opcional",
  disabled: "Desativado",
};

export function UsuariosTab({
  perfis,
  permissoes,
}: {
  perfis: PerfilItem[];
  permissoes: PermissaoItem[];
}) {
  const usuarios = useAsyncAction(() => listUsuarios());
  const convites = useAsyncAction(() => listConvites());
  const obras = useAsyncAction(() => listObras());

  const [mode, setMode] = useState<"convite" | "editar">("convite");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [usuarioId, setUsuarioId] = useState("");
  const [perfilCodigo, setPerfilCodigo] = useState("");
  const [twoFactorPolicy, setTwoFactorPolicy] = useState("required");
  const [ativo, setAtivo] = useState(true);
  const [obraIds, setObraIds] = useState<string[]>([]);
  const [permissoesEfetivas, setPermissoesEfetivas] = useState<Record<string, boolean>>({});
  const [showPermissoes, setShowPermissoes] = useState(false);
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
  const usuarioList: UsuarioItem[] = usuarios.data ?? [];

  const perfisAtribuiveis = useMemo(
    () => perfis.filter((perfil) => perfil.codigo !== "superadmin_2lock"),
    [perfis],
  );

  const perfilSelecionado = perfisAtribuiveis.find((perfil) => perfil.codigo === perfilCodigo);

  const obrasDisponiveis = useMemo(() => {
    if (perfilSelecionado?.codigo === "supervisor_empresa") {
      return obraList.filter((obra) => obra.tipo === "escritorio");
    }
    return obraList;
  }, [perfilSelecionado, obraList]);

  const padraoDoPerfil = useMemo(() => {
    const set = new Set(perfilSelecionado?.permissoes ?? []);
    const map: Record<string, boolean> = {};
    for (const permissao of permissoes) map[permissao.codigo] = set.has(permissao.codigo);
    return map;
  }, [perfilSelecionado, permissoes]);

  function aplicarPerfil(codigo: string) {
    setPerfilCodigo(codigo);
    const perfil = perfisAtribuiveis.find((item) => item.codigo === codigo);
    const set = new Set(perfil?.permissoes ?? []);
    const map: Record<string, boolean> = {};
    for (const permissao of permissoes) map[permissao.codigo] = set.has(permissao.codigo);
    setPermissoesEfetivas(map);
  }

  function resetForm() {
    setNome("");
    setEmail("");
    setUsuarioId("");
    setPerfilCodigo("");
    setObraIds([]);
    setPermissoesEfetivas({});
    setTwoFactorPolicy("required");
    setAtivo(true);
    setShowPermissoes(false);
  }

  function carregarUsuario(usuario: UsuarioItem) {
    setMode("editar");
    setUsuarioId(String(usuario.id));
    setNome(usuario.nome);
    setEmail(usuario.email);
    setTwoFactorPolicy(usuario.twoFactorPolicy);
    setAtivo(usuario.ativo);

    setPerfilCodigo(usuario.perfilCodigo);
    setObraIds(usuario.obras.map((item) => item.obraId));

    const perfil = perfis.find((item) => item.codigo === usuario.perfilCodigo);
    const set = new Set(perfil?.permissoes ?? []);
    const map: Record<string, boolean> = {};
    for (const permissao of permissoes) map[permissao.codigo] = set.has(permissao.codigo);
    for (const override of usuario.overrides) map[override.permissaoCodigo] = override.concedida;
    setPermissoesEfetivas(map);
    setShowPermissoes(true);
    setFeedback(null);
  }

  function handleObraChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const selected = Array.from(event.target.selectedOptions).map((option) => option.value);
    setObraIds(selected);
  }

  const overrides = useMemo(
    () =>
      permissoes
        .filter((permissao) => {
          const atual = permissoesEfetivas[permissao.codigo] === true;
          return atual !== (padraoDoPerfil[permissao.codigo] === true);
        })
        .map((permissao) => ({
          permissaoCodigo: permissao.codigo,
          concedida: permissoesEfetivas[permissao.codigo] === true,
        })),
    [padraoDoPerfil, permissoes, permissoesEfetivas],
  );

  async function submit() {
    setFeedback(null);
    setSaving(true);
    try {
      const obrasPayload = obraIds.map((obraId, index) => ({
        obraId,
        perfilCodigo,
        principal: index === 0,
      }));

      if (mode === "convite") {
        await createConvite({
          data: { nome, email, perfilCodigo, twoFactorPolicy, obras: obrasPayload, overrides },
        });
        setFeedback("Pré-cadastro criado. O acesso será liberado no primeiro login.");
        resetForm();
      } else {
        await updateUsuarioAcessos({
          data: {
            usuarioId: Number(usuarioId),
            obras: obrasPayload,
            overrides,
            twoFactorPolicy,
            ativo,
          },
        });
        setFeedback("Acessos do usuário atualizados.");
      }
      await Promise.all([reload(), reloadConvites()]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  }

  const formValid =
    obraIds.length > 0 &&
    perfilCodigo &&
    (mode === "convite" ? nome.trim() && email.trim() && twoFactorPolicy : usuarioId);

  const usuarioRows = usuarioList.map((row) => ({
    nome: row.nome,
    email: row.email,
    status: row.ativo ? "Ativo" : "Inativo",
    obra: row.obras.length > 0 ? row.obras.map((item) => item.obraNome).join(", ") : "-",
    funcao: perfilLabel(perfis, row.perfilCodigo),
    doisFatores: TWO_FACTOR_LABEL[row.twoFactorPolicy] ?? row.twoFactorPolicy,
    permissoes: row.overrides.length > 0 ? `${row.overrides.length} ajuste(s)` : "Padrão da função",
    acoes: row,
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

  return (
    <div className="page-stack">
      <div className="access-tabs">
        <button
          className={`segmented ${mode === "convite" ? "is-active" : ""}`}
          onClick={() => {
            setMode("convite");
            resetForm();
          }}
          type="button"
        >
          Pré-cadastrar usuário
        </button>
        <button
          className={`segmented ${mode === "editar" ? "is-active" : ""}`}
          onClick={() => setMode("editar")}
          type="button"
        >
          Editar usuário existente
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
            <select
              onChange={(event) => {
                const found = usuarioList.find((item) => String(item.id) === event.target.value);
                if (found) carregarUsuario(found);
                else resetForm();
              }}
              value={usuarioId}
            >
              <option value="">Selecione</option>
              {usuarioList.map((row) => (
                <option key={row.id} value={String(row.id)}>
                  {row.nome} — {row.email}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="field">
          <span>Função</span>
          <select onChange={(event) => aplicarPerfil(event.target.value)} value={perfilCodigo}>
            <option value="">Selecione</option>
            {perfisAtribuiveis.map((perfil) => (
              <option key={perfil.codigo} value={perfil.codigo}>
                {perfil.nome}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Obras</span>
          <select
            className="multi-select"
            disabled={obrasDisponiveis.length === 0}
            multiple
            onChange={handleObraChange}
            value={obraIds}
          >
            {obrasDisponiveis.length === 0 ? (
              <option disabled>Nenhuma obra disponível para esta função</option>
            ) : (
              obrasDisponiveis.map((obra) => (
                <option key={obra.id} value={obra.id}>
                  {obra.tipo === "escritorio" ? "ESCRITORIO" : obra.nome}
                </option>
              ))
            )}
          </select>
          <p className="field-hint">
            Mantenha Ctrl (Windows) ou Cmd (Mac) pressionado para selecionar várias.
          </p>
        </label>

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

        {mode === "editar" ? (
          <label className="field">
            <span>Status</span>
            <select
              onChange={(event) => setAtivo(event.target.value === "ativo")}
              value={ativo ? "ativo" : "inativo"}
            >
              <option value="ativo">Ativo</option>
              <option value="inativo">Inativo</option>
            </select>
          </label>
        ) : null}
      </div>

      <div className="content-band">
        <ShieldCheck aria-hidden="true" size={16} />
        <div>
          <h3>Permissões deste usuário</h3>
          <p>
            Começa no padrão da função escolhida. Ajuste aqui apenas o que muda para este usuário —
            {overrides.length > 0
              ? ` ${overrides.length} ajuste(s) fora do padrão.`
              : " nenhum ajuste no momento."}
          </p>
        </div>
        <button
          className="button ghost"
          onClick={() => setShowPermissoes((value) => !value)}
          type="button"
        >
          <Pencil aria-hidden="true" size={14} />
          {showPermissoes ? "Ocultar" : "Editar permissões"}
        </button>
      </div>

      {showPermissoes ? (
        <div className="role-chips permission-editor">
          {permissoes.map((permissao) => {
            const on = permissoesEfetivas[permissao.codigo] === true;
            const custom = on !== (padraoDoPerfil[permissao.codigo] === true);
            return (
              <button
                className={`role-chip ${on ? "is-on" : "is-off"} ${custom ? "is-custom" : ""}`}
                key={permissao.codigo}
                onClick={() =>
                  setPermissoesEfetivas((atual) => ({ ...atual, [permissao.codigo]: !on }))
                }
                type="button"
              >
                {on ? (
                  <Check aria-hidden="true" size={12} />
                ) : (
                  <X aria-hidden="true" size={12} />
                )}
                {permissao.nome}
                {custom ? <em>ajustado</em> : null}
              </button>
            );
          })}
          {perfilCodigo ? null : <p className="hint">Escolha a função primeiro.</p>}
        </div>
      ) : null}

      <div className="section-actions">
        <button
          className="button primary"
          disabled={saving || !formValid}
          onClick={() => void submit()}
          type="button"
        >
          <UserPlus aria-hidden="true" size={14} />
          {mode === "convite" ? "Pré-cadastrar e atribuir" : "Salvar alterações"}
        </button>
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

      <p className="hint">Nenhuma senha é armazenada pelo LinkAI.</p>
      {feedback ? <p className="hint">{feedback}</p> : null}
      {usuarios.error ? <p className="hint">{usuarios.error}</p> : null}

      <DataTable
        columns={[
          { key: "nome", label: "Nome" },
          { key: "email", label: "E-mail" },
          { key: "status", label: "Status" },
          { key: "obra", label: "Obras" },
          { key: "funcao", label: "Função" },
          { key: "doisFatores", label: "2FA" },
          { key: "permissoes", label: "Permissões" },
          {
            key: "acoes",
            label: "",
            render: (row: Record<string, unknown>) => (
              <button
                className="button ghost"
                onClick={() => carregarUsuario(row["acoes"] as UsuarioItem)}
                type="button"
              >
                <Pencil aria-hidden="true" size={12} />
                Editar
              </button>
            ),
          },
        ]}
        emptyLabel={usuarios.loading ? "Carregando..." : "Nenhum usuário na sua empresa."}
        rows={usuarioRows as unknown as Record<string, unknown>[]}
      />

      <div className="content-band">
        <div>
          <h3>Convites pendentes</h3>
          <p>Vínculo de empresa, obras, função e permissões aplicado no primeiro acesso.</p>
        </div>
      </div>

      <DataTable
        columns={[
          { key: "nome", label: "Nome" },
          { key: "email", label: "E-mail" },
          { key: "obra", label: "Obra principal" },
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
