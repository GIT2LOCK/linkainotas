import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle } from "lucide-react";

const REASONS: Record<string, string> = {
  start_failed: "Não foi possível iniciar o login. Verifique a configuração do Ariia.",
  missing_code: "O Ariia não devolveu um código de autorização.",
  expired_state: "Sua tentativa de login expirou. Tente novamente.",
  state_mismatch: "A validação de segurança do login falhou. Tente novamente.",
  inactive_user: "Seu acesso ao Linkai está inativo. Fale com o administrador.",
  callback_failed: "Falha ao concluir o login. Tente novamente em instantes.",
  access_denied: "Você recusou a autorização no Ariia.",
};

export const Route = createFileRoute("/auth/error")({
  validateSearch: (search: Record<string, unknown>) => ({
    reason: typeof search['reason'] === "string" ? search['reason'] : "",
  }),
  head: () => ({
    meta: [
      { title: "Falha no login | Linkai" },
      { name: "description", content: "Não foi possível concluir o login no Linkai." },
      { property: "og:title", content: "Falha no login | Linkai" },
      { property: "og:description", content: "Não foi possível concluir o login no Linkai." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: AuthError,
});

function AuthError() {
  const { reason } = Route.useSearch();
  const message = REASONS[reason] ?? "Não foi possível concluir o login no Linkai.";

  return (
    <main className="flex min-h-screen items-center justify-center bg-neutral-950 px-4">
      <section className="w-full max-w-sm rounded-3xl border border-glass-border bg-glass p-8 text-center backdrop-blur-2xl">
        <AlertTriangle className="mx-auto h-8 w-8 text-brand" />
        <h1 className="mt-4 text-xl font-semibold text-glass-foreground">Login não concluído</h1>
        <p className="mt-3 text-sm text-glass-muted">{message}</p>
        <a
          href="/api/auth/login"
          className="mt-7 block w-full rounded-xl bg-brand py-3 text-sm font-semibold text-brand-foreground transition-all hover:brightness-110"
        >
          Tentar novamente
        </a>
      </section>
    </main>
  );
}