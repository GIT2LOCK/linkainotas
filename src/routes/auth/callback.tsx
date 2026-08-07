import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

import { supabase } from "@/integrations/supabase/client";
import { completeAriiaLogin } from "@/modules/auth/auth.functions";
import { SIGN_IN_PATH, sanitizeRedirectPath } from "@/modules/auth/config";

export const Route = createFileRoute("/auth/callback")({
  // A sessão Supabase vive no browser: nada aqui pode rodar no servidor.
  ssr: false,
  head: () => ({
    meta: [
      { title: "Concluindo acesso | Linkai" },
      {
        name: "description",
        content: "Finalizando a autenticação segura da sua conta Ariia no Linkai.",
      },
      { name: "robots", content: "noindex" },
      { property: "og:title", content: "Concluindo acesso | Linkai" },
      { property: "og:description", content: "Finalizando a autenticação no Linkai." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: AuthCallback,
  errorComponent: ({ error }) => <CallbackShell message={error.message} isError />,
});

function AuthCallback() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    const params = new URLSearchParams(window.location.search);
    const oauthError = params.get("error_description") ?? params.get("error");
    const code = params.get("code");
    const state = params.get("state");

    if (oauthError) {
      setError(oauthError);
      return;
    }
    if (!code || !state) {
      setError("Retorno do Ariia incompleto: código de autorização ausente.");
      return;
    }

    void (async () => {
      try {
        const result = await completeAriiaLogin({ data: { code, state } });

        // Converte o token de uso único em uma sessão Supabase nativa.
        const { error: sessionError } = await supabase.auth.verifyOtp({
          type: "email",
          token_hash: result.tokenHash,
        });
        if (sessionError) throw new Error(sessionError.message);

        window.history.replaceState({}, "", window.location.pathname);
        navigate({ to: sanitizeRedirectPath(result.redirectTo), replace: true });
      } catch (cause) {
        console.error(cause);
        setError(cause instanceof Error ? cause.message : "Falha ao concluir o acesso.");
      }
    })();
  }, [navigate]);

  if (error) return <CallbackShell message={error} isError />;
  return <CallbackShell message="Validando sua identidade no Ariia…" />;
}

function CallbackShell({ message, isError }: { message: string; isError?: boolean }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-neutral-950 px-4">
      <div className="w-full max-w-sm rounded-3xl border border-glass-border bg-glass p-8 text-center backdrop-blur-2xl">
        {!isError ? (
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-brand" />
        ) : null}
        <h1 className="mt-4 text-lg font-semibold text-glass-foreground">
          {isError ? "Não foi possível entrar" : "Concluindo acesso"}
        </h1>
        <p className="mt-2 text-sm text-glass-muted">{message}</p>
        {isError ? (
          <a
            href={SIGN_IN_PATH}
            className="mt-6 inline-flex items-center justify-center rounded-xl bg-brand px-4 py-2.5 text-sm font-semibold text-brand-foreground"
          >
            Tentar novamente
          </a>
        ) : null}
      </div>
    </main>
  );
}