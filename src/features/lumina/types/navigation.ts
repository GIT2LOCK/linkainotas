import type { LucideIcon } from "lucide-react";
import type { NavigationAccess } from "@/lib/auth/permissions";

export type PageKey =
  | "home"
  | "processar-pdfs"
  | "lancar-notas"
  | "planilhas"
  | "supabase"
  | "arquivos"
  | "ia"
  | "historico"
  | "configuracoes"
  | "logs";

export interface NavigationItem {
  group: "Operação" | "Dados" | "Sistema";
  key: PageKey;
  label: string;
  icon: LucideIcon;
  access?: NavigationAccess;
}
