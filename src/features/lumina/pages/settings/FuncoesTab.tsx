import { Check, ShieldCheck } from "lucide-react";

import type { PerfilItem, PermissaoItem } from "../../services/access.functions";

const ESCOPO_LABEL: Record<string, string> = {
  plataforma: "Plataforma",
  empresa: "Empresa",
  obra: "Obra",
};

export function FuncoesTab({
  perfis,
  permissoes,
}: {
  perfis: PerfilItem[];
  permissoes: PermissaoItem[];
}) {
  return (
    <div className="page-stack">
      <div className="content-band">
        <ShieldCheck aria-hidden="true" size={16} />
        <div>
          <h3>Funções internas</h3>
          <p>
            Superadmin 2LOCK não pode ser atribuído a uma obra. Supervisor da empresa é atribuído
            somente ao ESCRITORIO. Matriz somente leitura.
          </p>
        </div>
      </div>

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
              {perfis.length === 0 ? (
                <tr>
                  <td className="empty-cell" colSpan={permissoes.length + 2}>
                    Nenhuma função disponível.
                  </td>
                </tr>
              ) : (
                perfis.map((perfil) => (
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
    </div>
  );
}
