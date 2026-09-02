export type AppAccessRole = "common" | "admin" | "superadmin";

export type NavigationAccess = "common" | "admin" | "superadmin";

export function getAccessRole(permission: string | null | undefined): AppAccessRole {
  const normalized = normalizePermission(permission);

  // Perfis internos do LinkAI (fonte de verdade) + valores legados do Ariia.
  if (
    normalized === "superadmin2lock" ||
    normalized === "superadmin" ||
    normalized === "superadministrador"
  ) {
    return "superadmin";
  }

  if (
    normalized === "supervisorempresa" ||
    normalized === "admin" ||
    normalized === "administrador"
  ) {
    return "admin";
  }

  return "common";
}

export function canAccessNavigation(
  required: NavigationAccess | undefined,
  role: AppAccessRole,
): boolean {
  if (!required || required === "common") return true;
  if (required === "admin") return role === "admin" || role === "superadmin";
  return role === "superadmin";
}

const PERFIL_LABELS: Record<string, string> = {
  superadmin2lock: "Superadmin 2LOCK",
  supervisorempresa: "Supervisor da empresa",
  gestorobra: "Gestor de obra",
  fiscalobra: "Fiscal de obra",
  financeiroobra: "Financeiro da obra",
  comprasobra: "Compras da obra",
  consultaobra: "Consulta da obra",
  semacesso: "Sem acesso",
};

export function getRoleLabel(permission: string | null | undefined): string {
  const normalized = normalizePermission(permission);
  const interno = PERFIL_LABELS[normalized];
  if (interno) return interno;

  const role = getAccessRole(permission);

  if (role === "superadmin") return "Superadmin";
  if (role === "admin") return "Admin";
  return "Usuário";
}


function normalizePermission(permission: string | null | undefined): string {
  return (permission ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}
