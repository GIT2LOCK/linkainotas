export type AppAccessRole = "common" | "admin" | "superadmin";

export type NavigationAccess = "common" | "admin" | "superadmin";

export function getAccessRole(permission: string | null | undefined): AppAccessRole {
  const normalized = normalizePermission(permission);

  if (normalized === "superadmin" || normalized === "superadministrador") {
    return "superadmin";
  }

  if (normalized === "admin" || normalized === "administrador") {
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

export function getRoleLabel(permission: string | null | undefined): string {
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
