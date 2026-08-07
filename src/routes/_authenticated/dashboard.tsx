import { createFileRoute } from "@tanstack/react-router";
import { LogOut, ShieldCheck } from "lucide-react";

import { useAuth } from "@/modules/auth/AuthProvider";
import { useProfile } from "@/modules/auth/useProfile";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [
      { title: "Painel | Linkai" },
      {
        name: "description",
        content: "Painel do Linkai com sua identidade sincronizada a partir do Ariia.",
      },
      { name: "robots", content: "noindex" },
      { property: "og:title", content: "Painel | Linkai" },
      { property: "og:description", content: "Painel interno do Linkai." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: DashboardPage,
});

function DashboardPage() {
  const { user, signOut } = useAuth();
  const { data: profile, isLoading } = useProfile();

  return (
    <main className="min-h-screen bg-neutral-950 px-6 py-10 text-glass-foreground">
      <div className="mx-auto max-w-3xl">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Painel do Linkai</h1>
            <p className="mt-1 text-sm text-glass-muted">
              Identidade fornecida pelo Ariia e espelhada localmente.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void signOut()}
            className="inline-flex items-center gap-2 rounded-xl border border-glass-border bg-glass px-4 py-2 text-sm font-medium backdrop-blur-xl transition-colors hover:brightness-110"
          >
            <LogOut className="h-4 w-4" />
            Sair
          </button>
        </header>

        <section className="mt-8 rounded-3xl border border-glass-border bg-glass p-6 backdrop-blur-2xl">
          <div className="flex items-center gap-2 text-sm text-brand">
            <ShieldCheck className="h-4 w-4" />
            Sessão autenticada
          </div>

          <dl className="mt-5 grid gap-4 sm:grid-cols-2">
            <Item label="E-mail" value={user?.email ?? "—"} />
            <Item label="Nome" value={isLoading ? "carregando…" : (profile?.nome ?? "—")} />
            <Item label="ID no Linkai" value={user?.id ?? "—"} />
            <Item
              label="ID no Ariia"
              value={isLoading ? "carregando…" : (profile?.ariia_user_id ?? "—")}
            />
          </dl>
        </section>
      </div>
    </main>
  );
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-glass-border/60 bg-glass/60 p-4">
      <dt className="text-xs uppercase tracking-wide text-glass-muted">{label}</dt>
      <dd className="mt-1 break-all text-sm font-medium">{value}</dd>
    </div>
  );
}