import { useMemo, useState } from "react";
import { Check, Search, ShieldCheck } from "lucide-react";

import type { PerfilItem, PermissaoItem } from "../../services/access.functions";

const ESCOPO_LABEL: Record<string, string> = {
  plataforma: "Plataforma",
  empresa: "Empresa",
  obra: "Obra",
};

const ESCOPO_HINT: Record<string, string> = {
  plataforma: "Acesso a todas as empresas. Não pode ser atribuído a uma obra.",
  empresa: "Acesso a todas as obras da empresa. Atribuído somente ao ESCRITORIO.",
  obra: "Acesso restrito à obra em que o usuário foi atribuído.",
};

export function FuncoesTab({
  perfis,
  permissoes,
}: {
  perfis: PerfilItem[];
  permissoes: PermissaoItem[];
}) {
  const [busca, setBusca] = useState("");
  const [showMatriz, setShowMatriz] = useState(false);

  const filtrados = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) return perfis;
    return perfis.filter(
      (perfil) =>
        perfil.nome.toLowerCase().includes(termo) ||
        perfil.codigo.toLowerCase().includes(termo) ||
        perfil.permissoes.some((codigo) => codigo.toLowerCase().includes(termo)),
    );
  }, [busca, perfis]);

  const nomePermissao = useMemo(() => {
    const map = new Map<string, string>();
    for (const permissao of permissoes) map.set(permissao.codigo, permissao.nome);
    return map;
  }, [permissoes]);

  return (
    <div className="page-stack">
      <div className="content-band">
        <ShieldCheck aria-hidden="true" size={16} />
        <div>
          <h3>Como as funções funcionam</h3>
          <p>
            Cada usuário recebe uma função em uma obra. A função define o que ele pode fazer, e o
            escopo define onde. Esta lista é somente leitura.
          </p>
        </div>
      </div>

      <div className="access-form">
        <label className="field">
          <span>Buscar função ou permissão</span>
          <input
            onChange={(event) => setBusca(event.target.value)}
            placeholder="Ex.: gestor, lançar notas"
            value={busca}
          />
        </label>
        <button
          className="button ghost"
          onClick={() => setShowMatriz((value) => !value)}
          type="button"
        >
          <Search aria-hidden="true" size={14} />
          {showMatriz ? "Ver em cartões" : "Ver matriz completa"}
        </button>
      </div>

      {showMatriz ? (
        <div className="table-shell">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Função</th>
                  <th>Escopo</th>
                  {permissoes.map((permissao) => (
                    <th key={permissao.codigo}>{permissao.nome}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtrados.length === 0 ? (
                  <tr>
                    <td className="empty-cell" colSpan={permissoes.length + 2}>
                      Nenhuma função encontrada.
                    </td>
                  </tr>
                ) : (
                  filtrados.map((perfil) => (
                    <tr key={perfil.codigo}>
                      <td>{perfil.nome}</td>
                      <td>{ESCOPO_LABEL[perfil.escopo] ?? perfil.escopo}</td>
                      {permissoes.map((permissao) => (
                        <td key={permissao.codigo}>
                          {perfil.permissoes.includes(permissao.codigo) ? (
                            <Check aria-label="Permitido" size={14} />
                          ) : (
                            <span aria-label="Não permitido">—</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="role-grid">
          {filtrados.length === 0 ? (
            <p className="hint">Nenhuma função encontrada.</p>
          ) : (
            filtrados.map((perfil) => {
              const negadas = permissoes.filter(
                (permissao) => !perfil.permissoes.includes(permissao.codigo),
              );

              return (
                <article className="role-card" key={perfil.codigo}>
                  <header>
                    <h4>{perfil.nome}</h4>
                    <span className={`role-scope scope-${perfil.escopo}`}>
                      {ESCOPO_LABEL[perfil.escopo] ?? perfil.escopo}
                    </span>
                  </header>
                  <p className="role-hint">{ESCOPO_HINT[perfil.escopo] ?? ""}</p>

                  <span className="role-legend">
                    Pode ({perfil.permissoes.length}/{permissoes.length})
                  </span>
                  <div className="role-chips">
                    {perfil.permissoes.length === 0 ? (
                      <span className="role-chip is-off">Somente visualizar o próprio acesso</span>
                    ) : (
                      perfil.permissoes.map((codigo) => (
                        <span className="role-chip is-on" key={codigo}>
                          <Check aria-hidden="true" size={12} />
                          {nomePermissao.get(codigo) ?? codigo}
                        </span>
                      ))
                    )}
                  </div>

                  {negadas.length > 0 ? (
                    <>
                      <span className="role-legend">Não pode</span>
                      <div className="role-chips">
                        {negadas.map((permissao) => (
                          <span className="role-chip is-off" key={permissao.codigo}>
                            {permissao.nome}
                          </span>
                        ))}
                      </div>
                    </>
                  ) : null}
                </article>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
