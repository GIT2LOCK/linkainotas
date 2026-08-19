import { Suspense, lazy, useMemo, useState } from "react";
import {
  Bot,
  Cloud,
  FileArchive,
  FileSpreadsheet,
  Files,
  House,
  LineChart,
  Play,
  ScrollText,
  Settings,
} from "lucide-react";

import { AppShell } from "./layouts/AppShell";
import type { NavigationItem, PageKey } from "./types/navigation";
import { canAccessNavigation, getAccessRole } from "@/lib/auth/permissions";
import "./styles/global.css";

const HomePage = lazy(() =>
  import("./pages/HomePage").then((module) => ({ default: module.HomePage })),
);
const ProcessPdfsPage = lazy(() =>
  import("./pages/ProcessPdfsPage").then((module) => ({ default: module.ProcessPdfsPage })),
);
const LaunchNotesPage = lazy(() =>
  import("./pages/LaunchNotesPage").then((module) => ({ default: module.LaunchNotesPage })),
);
const SpreadsheetsPage = lazy(() =>
  import("./pages/SpreadsheetsPage").then((module) => ({ default: module.SpreadsheetsPage })),
);
const CloudPage = lazy(() =>
  import("./pages/CloudPage").then((module) => ({ default: module.CloudPage })),
);
const FilesPage = lazy(() =>
  import("./pages/FilesPage").then((module) => ({ default: module.FilesPage })),
);
const AiPage = lazy(() => import("./pages/AiPage").then((module) => ({ default: module.AiPage })));
const HistoryPage = lazy(() =>
  import("./pages/HistoryPage").then((module) => ({ default: module.HistoryPage })),
);
const SettingsPage = lazy(() =>
  import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage })),
);
const LogsPage = lazy(() =>
  import("./pages/LogsPage").then((module) => ({ default: module.LogsPage })),
);

export interface LuminaSessionUser {
  nome: string;
  email: string;
  permissao: string | null;
  avatarUrl: string | null;
}

const navigation: NavigationItem[] = [
  { group: "Operação", key: "home", label: "Início", icon: House, access: "common" },
  {
    group: "Operação",
    key: "processar-pdfs",
    label: "Processar PDFs",
    icon: FileArchive,
    access: "common",
  },
  { group: "Operação", key: "lancar-notas", label: "Lançar Notas", icon: Play, access: "common" },
  { group: "Operação", key: "ia", label: "Inteligência Artificial", icon: Bot, access: "common" },
  { group: "Dados", key: "planilhas", label: "Planilhas", icon: FileSpreadsheet, access: "common" },
  { group: "Dados", key: "supabase", label: "Nuvem", icon: Cloud, access: "common" },
  { group: "Dados", key: "arquivos", label: "Arquivos", icon: Files, access: "common" },
  { group: "Sistema", key: "historico", label: "Histórico", icon: ScrollText, access: "common" },
  { group: "Sistema", key: "logs", label: "Logs", icon: LineChart, access: "admin" },
  {
    group: "Sistema",
    key: "configuracoes",
    label: "Configurações",
    icon: Settings,
    access: "common",
  },
];

export function LuminaApp({ user }: { user: LuminaSessionUser }) {
  const [selectedPage, setSelectedPage] = useState<PageKey>("home");
  const accessRole = getAccessRole(user.permissao);
  const availableNavigation = useMemo(
    () => navigation.filter((item) => canAccessNavigation(item.access, accessRole)),
    [accessRole],
  );
  const activePage = availableNavigation.some((item) => item.key === selectedPage)
    ? selectedPage
    : "home";

  const page = useMemo(() => {
    switch (activePage) {
      case "home":
        return <HomePage />;
      case "processar-pdfs":
        return <ProcessPdfsPage />;
      case "lancar-notas":
        return <LaunchNotesPage />;
      case "planilhas":
        return <SpreadsheetsPage />;
      case "supabase":
        return <CloudPage />;
      case "arquivos":
        return <FilesPage />;
      case "ia":
        return <AiPage />;
      case "historico":
        return <HistoryPage />;
      case "configuracoes":
        return <SettingsPage />;
      case "logs":
        return <LogsPage />;
      default:
        return <HomePage />;
    }
  }, [activePage]);

  return (
    <AppShell
      activePage={activePage}
      navigation={availableNavigation}
      onNavigate={(pageKey) => {
        if (availableNavigation.some((item) => item.key === pageKey)) {
          setSelectedPage(pageKey);
        }
      }}
      user={user}
    >
      <Suspense fallback={<div className="loading-panel">Carregando...</div>}>{page}</Suspense>
    </AppShell>
  );
}
