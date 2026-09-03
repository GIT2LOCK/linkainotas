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
  Activity,
  UserRound,
} from "lucide-react";

import { AppShell } from "./layouts/AppShell";
import type { NavigationItem, PageKey } from "./types/navigation";
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
const ActivitiesPage = lazy(() =>
  import("./pages/ActivitiesPage").then((module) => ({ default: module.ActivitiesPage })),
);
const ProfilePage = lazy(() =>
  import("./pages/ProfilePage").then((module) => ({ default: module.ProfilePage })),
);

export interface LuminaSessionUser {
  nome: string;
  email: string;
  permissao: string | null;
  avatarUrl: string | null;
  isPlatformSuperadmin?: boolean;
  permissoes?: string[];
}

const navigation: NavigationItem[] = [
  { group: "Operação", key: "home", label: "Início", icon: House, permissao: "home.view" },
  {
    group: "Operação",
    key: "processar-pdfs",
    label: "Processar PDFs",
    icon: FileArchive,
    permissao: "documents.process",
  },
  {
    group: "Operação",
    key: "lancar-notas",
    label: "Lançar Notas",
    icon: Play,
    permissao: "notes.launch",
  },
  {
    group: "Operação",
    key: "ia",
    label: "Inteligência Artificial",
    icon: Bot,
    permissao: "ai.use",
  },
  {
    group: "Dados",
    key: "planilhas",
    label: "Planilhas",
    icon: FileSpreadsheet,
    permissao: "spreadsheets.view",
  },
  { group: "Dados", key: "supabase", label: "Nuvem", icon: Cloud, permissao: "cloud.view" },
  { group: "Dados", key: "arquivos", label: "Arquivos", icon: Files, permissao: "files.view" },
  {
    group: "Sistema",
    key: "historico",
    label: "Histórico",
    icon: ScrollText,
    permissao: "history.view",
  },
  {
    group: "Sistema",
    key: "atividades",
    label: "Atividades",
    icon: Activity,
    permissao: "queue.monitor",
  },
  { group: "Sistema", key: "meu-perfil", label: "Meu Perfil", icon: UserRound },
  { group: "Sistema", key: "logs", label: "Logs", icon: LineChart, permissao: "logs.view" },
  {
    group: "Sistema",
    key: "configuracoes",
    label: "Configurações",
    icon: Settings,
    permissao: "access.manage",
  },
];

const ALL_PERMISSOES = ["access.manage", "works.manage", "records.manage"];

export function LuminaApp({ user }: { user: LuminaSessionUser }) {
  const [sessionUser, setSessionUser] = useState(user);
  const [selectedPage, setSelectedPage] = useState<PageKey>("home");
  const permissoes = useMemo(() => sessionUser.permissoes ?? [], [sessionUser.permissoes]);
  const isSuperadmin = sessionUser.isPlatformSuperadmin === true;
  const availableNavigation = useMemo(
    () =>
      navigation.filter(
        (item) => isSuperadmin || !item.permissao || permissoes.includes(item.permissao),
      ),
    [isSuperadmin, permissoes],
  );
  const activePage = availableNavigation.some((item) => item.key === selectedPage)
    ? selectedPage
    : (availableNavigation[0]?.key ?? "home");

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
        return <SettingsPage permissoes={isSuperadmin ? ALL_PERMISSOES : permissoes} />;
      case "atividades":
        return <ActivitiesPage />;
      case "meu-perfil":
        return (
          <ProfilePage
            initialUser={sessionUser}
            onProfileUpdated={(update) => setSessionUser((current) => ({ ...current, ...update }))}
          />
        );
      case "logs":
        return <LogsPage />;
      default:
        return <HomePage />;
    }
  }, [activePage, isSuperadmin, permissoes, sessionUser]);

  return (
    <AppShell
      activePage={activePage}
      navigation={availableNavigation}
      onNavigate={(pageKey) => {
        if (availableNavigation.some((item) => item.key === pageKey)) {
          setSelectedPage(pageKey);
        }
      }}
      user={sessionUser}
    >
      <Suspense fallback={<div className="loading-panel">Carregando...</div>}>{page}</Suspense>
    </AppShell>
  );
}
