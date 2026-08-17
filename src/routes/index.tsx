import { createFileRoute, redirect } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { ArrowRight, KeyRound, Loader2, Lock, Mail, ShieldCheck, User } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { BackgroundReel } from "@/components/BackgroundReel";
import linkaiLoginLogoUrl from "@/features/lumina/assets/linkai-logo.png";
import {
  loginWithAriia,
  signupWithAriia,
  verifyTwoFactor,
  type AuthStep,
} from "@/lib/auth/auth.functions";
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
          "Acesse o Linkai com sua conta corporativa para acompanhar notas, pedidos e medições das obras da Linka Engenharia.",
      },
      { property: "og:title", content: "Entrar | Linkai — Linka Engenharia" },
      { property: "og:description", content: "Login corporativo do Linkai." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: AuthScreen,
});

type Mode = "login" | "signup";
const LOGIN_REDIRECT_DELAY_MS = 1000;

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    const clean = error.message.replace(/^Error:\s*/, "");
    if (clean.startsWith("{") || clean.includes("[object"))
      return "Não foi possível concluir. Tente novamente.";
    return clean;
  }
  return "Não foi possível concluir. Tente novamente.";
}

function AuthScreen() {
  const login = useServerFn(loginWithAriia);
  const signup = useServerFn(signupWithAriia);
  const verify = useServerFn(verifyTwoFactor);

  const [mode, setMode] = useState<Mode>("login");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [code, setCode] = useState("");
  const [challenge, setChallenge] = useState<Extract<
    AuthStep,
    { step: "2fa" | "setup2fa" }
  > | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const isSignup = mode === "signup";

  async function handleStep(step: AuthStep) {
    if (step.step === "authenticated") {
      // Reload completo: garante que o SSR do /dashboard leia os cookies recém-criados.
      if (typeof window !== "undefined") {
        toast.success("Login Efetuado com sucesso");
        await new Promise((resolve) => window.setTimeout(resolve, LOGIN_REDIRECT_DELAY_MS));
        window.location.assign("/dashboard");
        return;
      }
      return;
    }
    setCode("");
    setChallenge(step);
  }

  async function submitCredentials(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const step = isSignup
        ? await signup({ data: { nome, email, senha } })
        : await login({ data: { email, senha } });
      await handleStep(step);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setPending(false);
    }
  }

  async function submitCode(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await handleStep(await verify({ data: { code } }));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setPending(false);
    }
  }

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
    setChallenge(null);
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12">
      <BackgroundReel />
      <div className="absolute inset-0 bg-neutral-950/55" />
      <div className="absolute inset-0 bg-gradient-to-t from-neutral-950/85 via-transparent to-neutral-950/60" />

      <section className="relative w-full max-w-sm rounded-3xl border border-glass-border bg-glass p-8 backdrop-blur-2xl [box-shadow:var(--shadow-glass)]">
        <div className="flex flex-col items-center gap-3">
          <img src={linkaiLoginLogoUrl} alt="LinkAI Engenharia" className="h-16 w-auto" />
        </div>

        {challenge ? (
          <form onSubmit={submitCode} className="mt-6">
            <h1 className="animate-fade-in text-center text-xl font-semibold tracking-tight text-glass-foreground">
              Verificação em duas etapas
            </h1>
            <p className="mt-2 animate-fade-in text-center text-sm text-glass-muted">
              {challenge.step === "setup2fa"
                ? "Escaneie o QR Code no seu aplicativo autenticador e informe o código gerado."
                : "Informe o código de 6 dígitos do seu aplicativo autenticador."}
            </p>

            {challenge.step === "setup2fa" && (
              <div className="mt-5 flex flex-col items-center gap-3">
                {challenge.qrCodeUrl && (
                  <img
                    src={challenge.qrCodeUrl}
                    alt="QR Code para configurar o autenticador"
                    className="h-40 w-40 rounded-xl bg-white p-2"
                  />
                )}
                <p className="text-center text-xs text-glass-muted">
                  Ou digite a chave:{" "}
                  <span className="font-mono tracking-wider text-glass-foreground">
                    {challenge.secret}
                  </span>
                </p>
              </div>
            )}

            <div className="mt-6">
              <Field icon={KeyRound}>
                <input
                  value={code}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="000000"
                  required
                  className="w-full bg-transparent text-center font-mono text-lg tracking-[0.4em] text-glass-foreground placeholder:text-glass-muted/60 focus:outline-none"
                />
              </Field>
            </div>

            {error && <ErrorText message={error} />}

            <SubmitButton pending={pending} label="Confirmar" />

            <button
              type="button"
              onClick={() => setChallenge(null)}
              className="mt-4 w-full text-center text-xs text-glass-muted transition-colors hover:text-glass-foreground"
            >
              Voltar
            </button>
          </form>
        ) : (
          <>
            <div className="relative mt-6 grid grid-cols-2 rounded-xl border border-glass-border bg-glass p-1 backdrop-blur-xl">
              <span
                className="absolute inset-y-1 w-[calc(50%-0.25rem)] rounded-lg bg-brand transition-transform duration-500 [transition-timing-function:cubic-bezier(0.22,1,0.36,1)]"
                style={{
                  transform: isSignup ? "translateX(calc(100% + 0.5rem))" : "translateX(0)",
                }}
              />
              {(["login", "signup"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => switchMode(value)}
                  className={`relative z-10 rounded-lg py-2 text-sm font-medium transition-colors ${
                    mode === value
                      ? "text-brand-foreground"
                      : "text-glass-muted hover:text-glass-foreground"
                  }`}
                >
                  {value === "login" ? "Entrar" : "Cadastrar"}
                </button>
              ))}
            </div>

            <h1
              key={`title-${mode}`}
              className="mt-6 animate-fade-in text-center text-xl font-semibold tracking-tight text-glass-foreground"
            >
              {isSignup ? "Criar sua conta" : "Bem-vindo ao Linkai"}
            </h1>
            <p
              key={`sub-${mode}`}
              className="mt-2 animate-fade-in text-center text-sm text-glass-muted"
            >
              {isSignup
                ? "Crie seu acesso ao ambiente corporativo Linkai"
                : "Entre com sua conta corporativa"}
            </p>

            <form onSubmit={submitCredentials} className="mt-6">
              <div
                className={`grid overflow-hidden transition-all duration-500 [transition-timing-function:cubic-bezier(0.22,1,0.36,1)] ${
                  isSignup ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
                }`}
              >
                <div className="min-h-0 pb-3">
                  <Field icon={User}>
                    <input
                      value={nome}
                      onChange={(event) => setNome(event.target.value)}
                      placeholder="Nome completo"
                      autoComplete="name"
                      required={isSignup}
                      disabled={!isSignup}
                      maxLength={120}
                      className="w-full bg-transparent text-sm text-glass-foreground placeholder:text-glass-muted focus:outline-none"
                    />
                  </Field>
                </div>
              </div>

              <div className="pb-3">
                <Field icon={Mail}>
                  <input
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    type="email"
                    placeholder="E-mail corporativo"
                    autoComplete="email"
                    required
                    maxLength={255}
                    className="w-full bg-transparent text-sm text-glass-foreground placeholder:text-glass-muted focus:outline-none"
                  />
                </Field>
              </div>

              <div className="pb-3">
                <Field icon={Lock}>
                  <input
                    value={senha}
                    onChange={(event) => setSenha(event.target.value)}
                    type="password"
                    placeholder="Senha"
                    autoComplete={isSignup ? "new-password" : "current-password"}
                    required
                    maxLength={200}
                    className="w-full bg-transparent text-sm text-glass-foreground placeholder:text-glass-muted focus:outline-none"
                  />
                </Field>
              </div>

              {error && <ErrorText message={error} />}

              <SubmitButton pending={pending} label={isSignup ? "Criar conta" : "Entrar"} />
            </form>
          </>
        )}

        <div className="mt-6 flex items-start gap-2.5 rounded-xl border border-glass-border bg-glass px-4 py-3 backdrop-blur-xl">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
          <p className="text-xs leading-relaxed text-glass-muted">
            Consulte nossa{" "}
            <a
              href="https://2lock.com.br/politica-de-privacidade/"
              target="_blank"
              rel="noreferrer"
              className="font-medium text-brand underline decoration-brand/50 underline-offset-2 transition-colors hover:text-brand-foreground"
            >
              Política de Privacidade
            </a>{" "}
            para saber como seus dados são tratados, protegidos e utilizados.
          </p>
        </div>
      </section>
    </main>
  );
}

function Field({ icon: Icon, children }: { icon: typeof Mail; children: React.ReactNode }) {
  return (
    <label className="flex items-center gap-3 rounded-xl border border-glass-border bg-glass px-4 py-3 backdrop-blur-xl transition-colors focus-within:border-brand/70">
      <Icon className="h-4 w-4 shrink-0 text-glass-muted" />
      {children}
    </label>
  );
}

function ErrorText({ message }: { message: string }) {
  return (
    <p role="alert" className="mt-1 animate-fade-in text-sm text-brand">
      {message}
    </p>
  );
}

function SubmitButton({ pending, label }: { pending: boolean; label: string }) {
  return (
    <button
      type="submit"
      disabled={pending}
      className="group mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-brand py-3.5 text-sm font-semibold text-brand-foreground shadow-lg transition-all hover:brightness-110 active:scale-[0.99] disabled:opacity-70"
    >
      {pending ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <>
          {label}
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </>
      )}
    </button>
  );
}
