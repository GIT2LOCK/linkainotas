import { useEffect, useState } from "react";

import { SectionHeader } from "../components/SectionHeader";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { listPerfisEPermissoes } from "../services/access.functions";
import { FuncoesTab } from "./settings/FuncoesTab";
import { ObrasTab } from "./settings/ObrasTab";
import { UsuariosTab } from "./settings/UsuariosTab";

type TabKey = "obras" | "usuarios" | "funcoes" | "geral";

const TABS: { key: TabKey; label: string }[] = [
  { key: "obras", label: "Obras" },
  { key: "usuarios", label: "Usuários" },
  { key: "funcoes", label: "Funções e permissões" },
  { key: "geral", label: "Geral" },
];

export function SettingsPage({ permissoes }: { permissoes: string[] }) {
  const [tab, setTab] = useState<TabKey>("obras");
  const catalog = useAsyncAction(() => listPerfisEPermissoes());
  const { run } = catalog;

  useEffect(() => {
    void run().catch(() => undefined);
  }, [run]);

  const canManageWorks = permissoes.includes("works.manage");
  const canManageAccess = permissoes.includes("access.manage");
  const perfis = catalog.data?.perfis ?? [];

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Sistema"
        title="Configurações"
        description="Obras, usuários, funções e permissões do controle interno de acessos."
      />

      <div className="access-tabs">
        {TABS.map((item) => (
          <button
            className={`segmented ${tab === item.key ? "is-active" : ""}`}
            key={item.key}
            onClick={() => setTab(item.key)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "obras" ? <ObrasTab canManage={canManageWorks} /> : null}
      {tab === "usuarios" ? (
        canManageAccess ? (
          <UsuariosTab perfis={perfis} permissoes={catalog.data?.permissoes ?? []} />
        ) : (
          <p className="hint">Você não tem permissão para administrar usuários.</p>
        )
      ) : null}
      {tab === "funcoes" ? (
        <FuncoesTab perfis={perfis} permissoes={catalog.data?.permissoes ?? []} />
      ) : null}
      {tab === "geral" ? (
        <div className="settings-grid">
          <div className="content-band">
            <h3>Credenciais</h3>
            <p>Valores sensíveis permanecem protegidos no ambiente local.</p>
          </div>
          <div className="content-band">
            <h3>Interface</h3>
            <p>Tema escuro e idioma português brasileiro.</p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
