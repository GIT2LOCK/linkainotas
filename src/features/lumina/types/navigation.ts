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
  | "atividades"
  | "configuracoes"
  | "meu-perfil"
  | "logs";

export interface NavigationItem {
  group:
    "Visão geral" | "Operação" | "Recursos" | "Dados" | "Monitoramento" | "Administração" | "Conta";
  key: PageKey;
  label: string;
  icon: LucideIcon;
  access?: NavigationAccess;
  /** Permissão interna do LinkAI exigida para ver o item. */
  permissao?: string;
}
