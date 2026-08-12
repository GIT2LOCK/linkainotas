import { createFileRoute } from "@tanstack/react-router";
import { HardHat, LogOut } from "lucide-react";

import linkaLogo from "@/assets/linka-logo-white.png.asset.json";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [
      { title: "Em desenvolvimento | Linkai — Linka Engenharia" },
      {
        name: "description",
        content: "O aplicativo Linkai está em desenvolvimento. Novas funcionalidades em breve.",
      },
      { property: "og:title", content: "Em desenvolvimento | Linkai" },
      { property: "og:description", content: "O aplicativo Linkai está em desenvolvimento." },
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
    <main className="flex min-h-screen flex-col bg-neutral-950 px-6 py-10 text-glass-foreground">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4">
        <img src={linkaLogo.url} alt="Linka Engenharia" className="h-10 w-auto" />
        <a
          href="/api/auth/logout"
          className="flex items-center gap-2 rounded-xl border border-glass-border bg-glass px-4 py-2 text-sm text-glass-muted backdrop-blur-xl transition-colors hover:text-glass-foreground"
        >
          <LogOut className="h-4 w-4" />
          Sair
        </a>
      </header>

      <section className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center text-center">
        <div className="w-full rounded-3xl border border-glass-border bg-glass p-10 backdrop-blur-2xl [box-shadow:var(--shadow-glass)]">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand/15 text-brand">
            <HardHat className="h-7 w-7" />
          </div>
          <h1 className="mt-6 text-2xl font-semibold tracking-tight">Aplicativo em desenvolvimento</h1>
          <p className="mt-3 text-sm leading-relaxed text-glass-muted">
            Olá, {user.nome}. Seu acesso está ativo, mas o Linkai ainda está em construção. Em
            breve você acompanhará notas, pedidos e medições das obras por aqui.
          </p>
          <p className="mt-6 text-xs text-glass-muted">{user.email}</p>
        </div>
      </section>
    </main>
  );
}