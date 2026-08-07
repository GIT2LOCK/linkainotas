import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Eye, EyeOff, Lock, Mail, User } from "lucide-react";
import linkaLogo from "@/assets/linka-logo-white.png.asset.json";
import constructionVideo from "@/assets/construction-bg.mp4.asset.json";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Entrar ou criar conta | Linka Engenharia" },
      {
        name: "description",
        content:
          "Acesse a plataforma da Linka Engenharia ou crie sua conta para acompanhar seus projetos e obras.",
      },
      { property: "og:title", content: "Entrar ou criar conta | Linka Engenharia" },
      {
        property: "og:description",
        content: "Login e cadastro da plataforma Linka Engenharia.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: AuthScreen,
});

type Mode = "login" | "signup";

function AuthScreen() {
  const [mode, setMode] = useState<Mode>("login");
  const [showPassword, setShowPassword] = useState(false);
  const isSignup = mode === "signup";

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12">
      <video
        src={constructionVideo.url}
        autoPlay
        muted
        loop
        playsInline
        aria-hidden="true"
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-neutral-950/55" />
      <div className="absolute inset-0 bg-gradient-to-t from-neutral-950/85 via-transparent to-neutral-950/60" />

      <section className="relative w-full max-w-sm rounded-3xl border border-glass-border bg-glass p-8 backdrop-blur-2xl [box-shadow:var(--shadow-glass)]">
        <div className="flex flex-col items-center gap-3">
          <img src={linkaLogo.url} alt="Linka Engenharia" className="h-11 w-auto" />
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-glass-foreground drop-shadow">
            {isSignup ? "Criar conta" : "Bem-vindo"}
          </h1>
          <p className="text-center text-sm text-glass-muted">
            {isSignup
              ? "Preencha seus dados para começar"
              : "Entre para continuar sua jornada"}
          </p>
        </div>

        <div className="mt-6 flex rounded-full border border-glass-border bg-glass p-1 backdrop-blur-xl">
          {(["login", "signup"] as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`flex-1 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                mode === m
                  ? "bg-brand text-brand-foreground shadow-md"
                  : "text-glass-muted hover:text-glass-foreground"
              }`}
            >
              {m === "login" ? "Entrar" : "Cadastrar"}
            </button>
          ))}
        </div>

        <form
          className="mt-6 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
          }}
        >
          {isSignup && (
            <Field icon={<User className="h-4 w-4" />}>
              <input
                type="text"
                name="name"
                required
                placeholder="Nome completo"
                className="w-full bg-transparent text-sm text-glass-foreground placeholder:text-glass-muted focus:outline-none"
              />
            </Field>
          )}

          <Field icon={<Mail className="h-4 w-4" />}>
            <input
              type="email"
              name="email"
              required
              placeholder="E-mail"
              className="w-full bg-transparent text-sm text-glass-foreground placeholder:text-glass-muted focus:outline-none"
            />
          </Field>

          <Field icon={<Lock className="h-4 w-4" />}>
            <input
              type={showPassword ? "text" : "password"}
              name="password"
              required
              placeholder="Senha"
              className="w-full bg-transparent text-sm text-glass-foreground placeholder:text-glass-muted focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
              className="text-glass-muted transition-colors hover:text-glass-foreground"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </Field>

          <button
            type="submit"
            className="mt-2 w-full rounded-xl bg-brand py-3 text-sm font-semibold text-brand-foreground shadow-lg transition-transform hover:brightness-110 active:scale-[0.99]"
          >
            {isSignup ? "Criar conta" : "Entrar"}
          </button>
        </form>

        <p className="mt-5 text-center text-xs text-glass-muted">
          {isSignup ? (
            <>
              Já tem conta?{" "}
              <button
                type="button"
                onClick={() => setMode("login")}
                className="font-medium text-glass-foreground underline-offset-4 hover:underline"
              >
                Entrar
              </button>
            </>
          ) : (
            <button
              type="button"
              className="underline-offset-4 transition-colors hover:text-glass-foreground hover:underline"
            >
              Esqueceu sua senha?
            </button>
          )}
        </p>
      </section>
    </main>
  );
}

function Field({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <label className="flex items-center gap-3 rounded-xl border border-glass-border bg-glass px-4 py-3 backdrop-blur-xl transition-colors focus-within:border-glass-foreground/60">
      <span className="text-glass-muted">{icon}</span>
      {children}
    </label>
  );
}
