import { SectionHeader } from "../components/SectionHeader";

export function AiPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Recursos"
        title="Inteligência artificial"
        description="Recursos inteligentes disponíveis para apoiar a análise dos seus documentos."
      />
      <div className="content-band">
        <h3>Análise assistida</h3>
        <p>Nenhum provedor de inteligência artificial está configurado neste ambiente.</p>
      </div>
    </div>
  );
}
