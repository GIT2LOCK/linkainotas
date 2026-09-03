import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { LogOut, Moon, Search, ShieldCheck, Sun } from "lucide-react";

import linkaiLogoDarkUrl from "../assets/linkai-logo.png";
import linkaiLogoLightUrl from "../assets/linkai-logo-light.png";
import type { LuminaSessionUser } from "../LuminaApp";
import type { NavigationItem, PageKey } from "../types/navigation";
import { getRoleLabel } from "@/lib/auth/permissions";

interface AppShellProps {
  activePage: PageKey;
  children: ReactNode;
  navigation: NavigationItem[];
  onNavigate: (page: PageKey) => void;
  user: LuminaSessionUser;
}

type LuminaTheme = "dark" | "light";

const themeStorageKey = "linkai-lumina-theme";
const navigationGroupOrder = [
  "Visão geral",
  "Operação",
  "Recursos",
  "Dados",
  "Monitoramento",
  "Administração",
  "Conta",
] as const;

export function AppShell({ activePage, children, navigation, onNavigate, user }: AppShellProps) {
  const [theme, setTheme] = useState<LuminaTheme>("dark");
  const [searchQuery, setSearchQuery] = useState("");
  const activeLabel = navigation.find((item) => item.key === activePage)?.label ?? "Início";
  const role = getRoleLabel(user.permissao);
  const initials = user.nome
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
  const navigationGroups = useMemo(
    () =>
      navigationGroupOrder
        .map((group) => ({
          group,
          items: navigation.filter((item) => item.group === group),
        }))
        .filter((group) => group.items.length > 0),
    [navigation],
  );
  const ThemeIcon = theme === "dark" ? Sun : Moon;

  useEffect(() => {
    const storedTheme = window.localStorage.getItem(themeStorageKey);

    if (storedTheme === "dark" || storedTheme === "light") {
      setTheme(storedTheme);
      return;
    }

    if (window.matchMedia?.("(prefers-color-scheme: light)").matches) {
      setTheme("light");
    }
  }, []);

  function toggleTheme() {
    setTheme((current) => {
      const nextTheme = current === "dark" ? "light" : "dark";
      window.localStorage.setItem(themeStorageKey, nextTheme);
      return nextTheme;
    });
  }

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedQuery = normalizeSearchText(searchQuery);

    if (!normalizedQuery) {
      return;
    }

    const matchingItem = navigation.find((item) =>
      normalizeSearchText(item.label).includes(normalizedQuery),
    );

    if (matchingItem) {
      onNavigate(matchingItem.key);
      setSearchQuery("");
    }
  }

  return (
    <div className={`lumina-app theme-${theme}`}>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="brand-card">
            <img
              className="brand-logo"
              src={theme === "light" ? linkaiLogoLightUrl : linkaiLogoDarkUrl}
              alt="LinkAI Engenharia"
            />
          </div>

          <nav className="nav-list" aria-label="Navegação principal">
            {navigationGroups.map((group) => (
              <div className="nav-group" key={group.group}>
                <div className="nav-section-title">{group.group}</div>
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const selected = item.key === activePage;

                  return (
                    <button
                      aria-current={selected ? "page" : undefined}
                      className={`nav-item ${selected ? "is-active" : ""}`}
                      key={item.key}
                      onClick={() => onNavigate(item.key)}
                      type="button"
                    >
                      <span className="nav-icon">
                        <Icon size={18} />
                      </span>
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            ))}
          </nav>

          <div className="sidebar-footer">
            <span className="status-dot" aria-hidden="true" />
            <div>
              <span>LinkAI Web</span>
              <strong>Automação Lumina e inteligência fiscal.</strong>
            </div>
          </div>
        </aside>

        <main className="main-panel">
          <header className="topbar">
            <div className="topbar-title">
              <span className="eyebrow">Workspace</span>
              <h1>{activeLabel}</h1>
            </div>

            <form className="search-box" onSubmit={handleSearchSubmit} role="search">
              <Search size={18} />
              <input
                aria-label="Pesquisar página"
                list="lumina-navigation-options"
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Pesquisar páginas"
                type="search"
                value={searchQuery}
              />
              <datalist id="lumina-navigation-options">
                {navigation.map((item) => (
                  <option key={item.key} value={item.label} />
                ))}
              </datalist>
            </form>

            <button
              aria-label="Abrir Meu Perfil"
              className="topbar-greeting profile-trigger"
              onClick={() => onNavigate("meu-perfil")}
              title="Abrir Meu Perfil"
              type="button"
            >
              <span className="user-initials">
                {user.avatarUrl ? <img alt="" src={user.avatarUrl} /> : initials || "LA"}
              </span>
              <div>
                <span className="eyebrow">{role}</span>
                <strong>{user.nome}</strong>
              </div>
            </button>

            <div className="topbar-actions">
              <button
                aria-label={theme === "dark" ? "Ativar tema claro" : "Ativar tema escuro"}
                className="icon-button"
                onClick={toggleTheme}
                title={theme === "dark" ? "Ativar tema claro" : "Ativar tema escuro"}
                type="button"
              >
                <ThemeIcon size={18} />
              </button>
              <span
                aria-label="Ambiente seguro"
                className="icon-button icon-status"
                role="img"
                title="Ambiente seguro"
              >
                <ShieldCheck size={18} />
              </span>
              <a aria-label="Sair" className="icon-button" href="/api/auth/logout" title="Sair">
                <LogOut size={18} />
              </a>
            </div>
          </header>
          <section className="page-surface">{children}</section>
        </main>
      </div>
    </div>
  );
}

function normalizeSearchText(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}
