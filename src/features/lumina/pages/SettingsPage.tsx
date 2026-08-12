import { SectionHeader } from "../components/SectionHeader";

export function SettingsPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Sistema"
        title="Configurações"
        description="Nuvem, OCR, IA, Excel, pastas padrão, Lumina, tema e idioma."
      />
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
    </div>
  );
}
