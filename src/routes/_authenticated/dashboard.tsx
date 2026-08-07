import { createFileRoute } from "@tanstack/react-router";
import { Building2, LogOut } from "lucide-react";

import linkaLogo from "@/assets/linka-logo-white.png.asset.json";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [
      { title: "Painel | Linkai — Linka Engenharia" },
      {
        name: "description",
        content: "Painel do Linkai: notas fiscais, pedidos e medições das obras.",
      },
      { property: "og:title", content: "Painel | Linkai" },
      { property: "og:description", content: "Painel operacional do Linkai." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const { user } = Route.useRouteContext();

  return (
    <main className="min-h-screen bg-neutral-950 px-6 py-10 text-glass-foreground">
      <header className="mx-auto flex max-w-5xl items-center justify-between gap-4">
        <img src={linkaLogo.url} alt="Linka Engenharia" className="h-10 w-auto" />
        <a
          href="/api/auth/logout"
          className="flex items-center gap-2 rounded-xl border border-glass-border bg-glass px-4 py-2 text-sm text-glass-muted backdrop-blur-xl transition-colors hover:text-glass-foreground"
        >
          <LogOut className="h-4 w-4" />
          Sair
        </a>
      </header>

      <section className="mx-auto mt-10 max-w-5xl rounded-3xl border border-glass-border bg-glass p-8 backdrop-blur-2xl">
        <h1 className="text-2xl font-semibold tracking-tight">Olá, {user.nome}</h1>
        <p className="mt-2 text-sm text-glass-muted">{user.email}</p>

        <dl className="mt-8 grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-glass-border p-5">
            <dt className="flex items-center gap-2 text-xs uppercase tracking-wide text-glass-muted">
              <Building2 className="h-4 w-4" /> Empresa
            </dt>
            <dd className="mt-2 text-lg font-medium">{user.empresaId ?? "Não vinculada"}</dd>
          </div>
          <div className="rounded-2xl border border-glass-border p-5">
            <dt className="text-xs uppercase tracking-wide text-glass-muted">Permissão</dt>
            <dd className="mt-2 text-lg font-medium">{user.permissao ?? "Padrão"}</dd>
          </div>
        </dl>
      </section>
    </main>
  );
}