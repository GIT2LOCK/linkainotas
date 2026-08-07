import { createFileRoute, redirect } from "@tanstack/react-router";
import { ArrowRight, ShieldCheck } from "lucide-react";
import linkaLogo from "@/assets/linka-logo-white.png.asset.json";
import { BackgroundReel } from "@/components/BackgroundReel";
import { getCurrentSession } from "@/lib/auth/session.functions";

export const Route = createFileRoute("/")({
  beforeLoad: async () => {
    const { user } = await getCurrentSession();
    if (user) throw redirect({ to: "/dashboard" });
  },
  head: () => ({
    meta: [
      { title: "Entrar | Linkai — Linka Engenharia" },
      {
        name: "description",
        content:
          "Acesse o Linkai com sua conta corporativa Ariia para acompanhar notas, pedidos e medições das obras da Linka Engenharia.",
      },
      { property: "og:title", content: "Entrar | Linkai — Linka Engenharia" },
      {
        property: "og:description",
        content: "Login corporativo do Linkai via Ariia.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: AuthScreen,
});

function AuthScreen() {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12">
      <BackgroundReel />
      <div className="absolute inset-0 bg-neutral-950/55" />
      <div className="absolute inset-0 bg-gradient-to-t from-neutral-950/85 via-transparent to-neutral-950/60" />

      <section className="relative w-full max-w-sm rounded-3xl border border-glass-border bg-glass p-8 backdrop-blur-2xl [box-shadow:var(--shadow-glass)]">
        <div className="flex flex-col items-center gap-3">
          <img src={linkaLogo.url} alt="Linka Engenharia" className="h-16 w-auto" />
          <h1 className="mt-2 animate-fade-in text-2xl font-semibold tracking-tight text-glass-foreground drop-shadow">
            Bem-vindo ao Linkai
          </h1>
          <p className="animate-fade-in text-center text-sm text-glass-muted">
            Acesse com sua conta corporativa Ariia
          </p>
        </div>

        <a
          href="/api/auth/login"
          className="group mt-8 flex w-full items-center justify-center gap-2 rounded-xl bg-brand py-3.5 text-sm font-semibold text-brand-foreground shadow-lg transition-all hover:brightness-110 active:scale-[0.99]"
        >
          Entrar com Ariia
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </a>

        <div className="mt-6 flex items-start gap-2.5 rounded-xl border border-glass-border bg-glass px-4 py-3 backdrop-blur-xl">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
          <p className="text-xs leading-relaxed text-glass-muted">
            O Linkai não armazena senhas. Sua identidade é validada pelo Ariia, o
            provedor de acesso corporativo da Linka Engenharia.
          </p>
        </div>
      </section>
    </main>
  );
}
