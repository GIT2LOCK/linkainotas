import { SectionHeader } from "../components/SectionHeader";

export function AiPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Operação"
        title="Inteligência Artificial"
        description="Configure quando a análise inteligente deve ser acionada."
      />
      <div className="content-band">
        <h3>Fallback inteligente</h3>
        <p>Sem provedores configurados no momento.</p>
      </div>
    </div>
  );
}
