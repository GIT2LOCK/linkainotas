import { useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";

import { startAriiaLogin } from "@/modules/auth/auth.functions";

export function SignInWithAriiaButton({ redirectTo }: { redirectTo?: string }) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setIsLoading(true);
    setError(null);
    try {
      const { authorizationUrl } = await startAriiaLogin({
        data: { origin: window.location.origin, redirectTo },
      });
      window.location.assign(authorizationUrl);
    } catch (cause) {
      console.error(cause);
      setError(
        cause instanceof Error ? cause.message : "Não foi possível iniciar o acesso.",
      );
      setIsLoading(false);
    }
  }

  return (
    <div className="w-full">
      <button
        type="button"
        onClick={handleClick}
        disabled={isLoading}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand py-3.5 text-sm font-semibold text-brand-foreground shadow-lg transition-transform hover:brightness-110 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-70"
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ArrowRight className="h-4 w-4" />
        )}
        {isLoading ? "Redirecionando…" : "Entrar com Ariia"}
      </button>
      {error ? (
        <p role="alert" className="mt-3 text-center text-xs text-red-300">
          {error}
        </p>
      ) : null}
    </div>
  );
}