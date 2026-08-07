import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { ShieldCheck } from "lucide-react";

import linkaLogo from "@/assets/linka-logo-white.png.asset.json";
import { BackgroundReel } from "@/components/BackgroundReel";
import { SignInWithAriiaButton } from "@/components/auth/SignInWithAriiaButton";
import { useAuth } from "@/modules/auth/AuthProvider";
import { AUTHENTICATED_HOME, sanitizeRedirectPath } from "@/modules/auth/config";

export const Route = createFileRoute("/")({
  validateSearch: (search: Record<string, unknown>) => ({
    redirect: typeof search["redirect"] === "string" ? (search["redirect"] as string) : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Entrar no Linkai | Linka Engenharia" },
      {
        name: "description",
        content:
          "Acesse o Linkai com sua conta Ariia. Autenticação única, segura e centralizada para as operações da Linka Engenharia.",
      },
      { property: "og:title", content: "Entrar no Linkai | Linka Engenharia" },
      {
        property: "og:description",
        content: "Acesso ao Linkai com autenticação única pela conta Ariia.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SignInScreen,
});

function SignInScreen() {
  const { redirect } = Route.useSearch();
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate({ to: sanitizeRedirectPath(redirect ?? AUTHENTICATED_HOME), replace: true });
    }
  }, [isAuthenticated, isLoading, navigate, redirect]);

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
            Sua identidade é gerenciada pelo Ariia. Entre com a sua conta para continuar.
          </p>
        </div>

        <div className="mt-8">
          <SignInWithAriiaButton redirectTo={sanitizeRedirectPath(redirect)} />
        </div>

        <div className="mt-6 flex items-start gap-2 rounded-2xl border border-glass-border/60 bg-glass/60 p-3 text-xs text-glass-muted">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
          <p>
            Login, cadastro, senha e verificação em duas etapas acontecem no Ariia. O Linkai
            não armazena senhas.
          </p>
        </div>
      </section>
    </main>
  );
}
