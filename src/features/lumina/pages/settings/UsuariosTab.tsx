import { useEffect, useMemo, useState } from "react";
import {
  BookmarkPlus,
  Check,
  Copy,
  History,
  Pencil,
  RefreshCw,
  ShieldCheck,
  UserPlus,
  X,
} from "lucide-react";

import { DataTable } from "../../components/DataTable";
import { useAsyncAction } from "../../hooks/useAsyncAction";
import {
  createConvite,
  createAccessModel,
  applyAccessModelToUser,
  listAccessHistory,
  listAccessModels,
  listConvites,
  listObras,
  listUsuarios,
  updateUsuarioAcessos,
  type ConviteItem,
  type AccessHistoryItem,
  type AccessModelItem,
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
  const modelos = useAsyncAction(() => listAccessModels());
  const historico = useAsyncAction(() => listAccessHistory());

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
  const [modelName, setModelName] = useState("");
  const [modelDescription, setModelDescription] = useState("");
  const [showModelForm, setShowModelForm] = useState(false);
  const [modelSaving, setModelSaving] = useState(false);
  const [applyingModelId, setApplyingModelId] = useState<string | null>(null);

  const reload = usuarios.run;
  const reloadConvites = convites.run;
  const reloadObras = obras.run;
  const reloadModels = modelos.run;
  const reloadHistory = historico.run;

  useEffect(() => {
    void reload().catch(() => undefined);
    void reloadConvites().catch(() => undefined);
    void reloadObras().catch(() => undefined);
    void reloadModels().catch(() => undefined);
    void reloadHistory().catch(() => undefined);
  }, [reload, reloadConvites, reloadObras, reloadModels, reloadHistory]);

  const obraList: ObraItem[] = obras.data ?? [];
  const usuarioList: UsuarioItem[] = usuarios.data ?? [];
  const modelList: AccessModelItem[] = modelos.data ?? [];
  const historyList: AccessHistoryItem[] = historico.data ?? [];

  const perfisAtribuiveis = useMemo(
    () => perfis.filter((perfil) => perfil.codigo !== "superadmin_2lock"),
    [perfis],
  );

  const perfilSelecionado = perfisAtribuiveis.find((perfil) => perfil.codigo === perfilCodigo);

  const modelEmpresaId = useMemo(() => {
    const selected = obraList.filter((obra) => obraIds.includes(obra.id));
    return selected[0]?.empresaId ?? null;
  }, [obraIds, obraList]);

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

    const codigo = usuario.perfilCodigo ?? "";
    setPerfilCodigo(codigo);
    setObraIds(usuario.obras.map((item) => item.obraId));

    const perfil = perfis.find((item) => item.codigo === codigo);
    const set = new Set(perfil?.permissoes ?? []);
    const map: Record<string, boolean> = {};
    for (const permissao of permissoes) map[permissao.codigo] = set.has(permissao.codigo);
    for (const override of usuario.overrides) map[override.permissaoCodigo] = override.concedida;
    setPermissoesEfetivas(map);
    setShowPermissoes(true);
    setFeedback(null);
  }

  function aplicarModeloNoFormulario(model: AccessModelItem) {
    const principal = model.obras.find((obra) => obra.principal) ?? model.obras[0];
    const codigo = principal?.perfilCodigo ?? model.perfilCodigo;
    setPerfilCodigo(codigo);
    setObraIds(model.obras.map((obra) => obra.obraId));
    setTwoFactorPolicy(model.twoFactorPolicy);

    const perfil = perfisAtribuiveis.find((item) => item.codigo === codigo);
    const defaults = new Set(perfil?.permissoes ?? []);
    const map: Record<string, boolean> = {};
    for (const permissao of permissoes) map[permissao.codigo] = defaults.has(permissao.codigo);
    for (const override of model.overrides) map[override.permissaoCodigo] = override.concedida;
    setPermissoesEfetivas(map);
    setShowPermissoes(true);
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
      await Promise.all([reload(), reloadConvites(), reloadHistory()]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  }

  async function salvarModelo() {
    setFeedback(null);
    if (!modelEmpresaId) {
      setFeedback("Selecione ao menos uma obra para identificar a empresa do modelo.");
      return;
    }

    setModelSaving(true);
    try {
      await createAccessModel({
        data: {
          empresaId: modelEmpresaId,
          nome: modelName,
          descricao: modelDescription,
          perfilCodigo,
          twoFactorPolicy,
          obras: obraIds.map((obraId, index) => ({
            obraId,
            perfilCodigo,
            principal: index === 0,
          })),
          overrides,
        },
      });
      setModelName("");
      setModelDescription("");
      setShowModelForm(false);
      setFeedback("Modelo salvo. Ele já pode ser reaplicado em um clique.");
      await Promise.all([reloadModels(), reloadHistory()]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error));
    } finally {
      setModelSaving(false);
    }
  }

  async function aplicarModelo(model: AccessModelItem) {
    if (mode === "convite" || !usuarioId) {
      aplicarModeloNoFormulario(model);
      setFeedback(`Modelo “${model.nome}” carregado no formulário.`);
      return;
    }

    setFeedback(null);
    setApplyingModelId(model.id);
    try {
      await applyAccessModelToUser({ data: { modelId: model.id, usuarioId: Number(usuarioId) } });
      const refreshed = await reload();
      const updated = refreshed.find((item) => item.id === Number(usuarioId));
      if (updated) carregarUsuario(updated);
      setFeedback(`Modelo “${model.nome}” aplicado ao usuário.`);
      await reloadHistory();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error));
    } finally {
      setApplyingModelId(null);
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

        <div className="field">
          <span>Obras</span>
          <details className="multi-picker">
            <summary>
              {obraIds.length === 0
                ? "Selecione as obras"
                : obrasDisponiveis
                    .filter((obra) => obraIds.includes(obra.id))
                    .map((obra) => (obra.tipo === "escritorio" ? "ESCRITORIO" : obra.nome))
                    .join(", ")}
            </summary>
            <div className="multi-picker-list">
              {obrasDisponiveis.length === 0 ? (
                <p className="field-hint">Nenhuma obra disponível para esta função</p>
              ) : (
                obrasDisponiveis.map((obra) => (
                  <label className="multi-picker-option" key={obra.id}>
                    <input
                      checked={obraIds.includes(obra.id)}
                      onChange={(event) =>
                        setObraIds((atual) =>
                          event.target.checked
                            ? [...atual, obra.id]
                            : atual.filter((id) => id !== obra.id),
                        )
                      }
                      type="checkbox"
                    />
                    <span>{obra.tipo === "escritorio" ? "ESCRITORIO" : obra.nome}</span>
                  </label>
                ))
              )}
            </div>
          </details>
        </div>


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

      <section className="access-models-panel">
        <div className="content-band access-models-header">
          <BookmarkPlus aria-hidden="true" size={16} />
          <div>
            <h3>Modelos de atribuição</h3>
            <p>
              Salve uma combinação de função, obras, 2FA e permissões para reaplicar sem repetir o
              preenchimento.
            </p>
          </div>
          <button
            className="button ghost"
            disabled={!formValid || modelSaving}
            onClick={() => setShowModelForm((value) => !value)}
            type="button"
          >
            <BookmarkPlus aria-hidden="true" size={14} />
            {showModelForm ? "Fechar" : "Salvar configuração atual"}
          </button>
        </div>

        {showModelForm ? (
          <div className="access-form access-model-form">
            <label className="field">
              <span>Nome do modelo</span>
              <input
                onChange={(event) => setModelName(event.target.value)}
                placeholder="Fiscal da obra"
                value={modelName}
              />
            </label>
            <label className="field">
              <span>Descrição (opcional)</span>
              <input
                onChange={(event) => setModelDescription(event.target.value)}
                placeholder="Acesso padrão para fiscais"
                value={modelDescription}
              />
            </label>
            <button
              className="button primary"
              disabled={modelSaving || !modelName.trim() || !formValid}
              onClick={() => void salvarModelo()}
              type="button"
            >
              <BookmarkPlus aria-hidden="true" size={14} />
              {modelSaving ? "Salvando..." : "Salvar modelo"}
            </button>
          </div>
        ) : null}

        {modelos.error ? <p className="hint">{modelos.error}</p> : null}
        {modelList.length > 0 ? (
          <div className="access-model-list">
            {modelList.map((model) => (
              <article className="access-model-row" key={model.id}>
                <div className="access-model-copy">
                  <strong>{model.nome}</strong>
                  <span>
                    {perfilLabel(perfis, model.perfilCodigo)} · {model.obras.length} obra(s) ·{" "}
                    {model.overrides.length} ajuste(s) · 2FA {TWO_FACTOR_LABEL[model.twoFactorPolicy] ?? model.twoFactorPolicy}
                  </span>
                  {model.descricao ? <small>{model.descricao}</small> : null}
                </div>
                <button
                  className="button ghost"
                  disabled={applyingModelId !== null}
                  onClick={() => void aplicarModelo(model)}
                  type="button"
                >
                  <Copy aria-hidden="true" size={13} />
                  {applyingModelId === model.id
                    ? "Aplicando..."
                    : mode === "editar" && usuarioId
                      ? "Aplicar ao usuário"
                      : "Usar no formulário"}
                </button>
              </article>
            ))}
          </div>
        ) : (
          <p className="hint">Nenhum modelo salvo ainda.</p>
        )}
      </section>

      <section className="access-history-panel">
        <div className="content-band access-models-header">
          <History aria-hidden="true" size={16} />
          <div>
            <h3>Histórico de alterações</h3>
            <p>Registro das configurações criadas, atualizadas e reaplicadas nesta empresa.</p>
          </div>
          <button
            className="button ghost"
            disabled={historico.loading}
            onClick={() => void reloadHistory().catch(() => undefined)}
            type="button"
          >
            <RefreshCw aria-hidden="true" size={14} />
            Atualizar histórico
          </button>
        </div>
        <DataTable
          columns={[
            { key: "acao", label: "Ação" },
            { key: "actor", label: "Operador" },
            { key: "target", label: "Alvo" },
            { key: "model", label: "Modelo" },
            { key: "resumo", label: "Resumo" },
            {
              key: "createdAt",
              label: "Data",
              render: (row: Record<string, unknown>) =>
                new Date(String(row["createdAt"])).toLocaleString("pt-BR"),
            },
          ]}
          emptyLabel={historico.loading ? "Carregando histórico..." : "Nenhuma alteração registrada."}
          rows={historyList.map((row) => ({
            acao: row.acao,
            actor: row.actorName ?? "Usuário atual",
            target: row.targetName
              ? `${row.targetName}${row.targetEmail ? ` · ${row.targetEmail}` : ""}`
              : "Configuração da empresa",
            model: row.modelName ?? "Configuração manual",
            resumo: row.resumo,
            createdAt: row.createdAt,
          }))}
        />
      </section>

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
