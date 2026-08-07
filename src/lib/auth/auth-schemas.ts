/** Schemas de validação compartilhados do login/cadastro. */
import { z } from "zod";

export const credentialsSchema = z.object({
  email: z.string().trim().email("Informe um e-mail válido.").max(255),
  senha: z.string().min(1, "Informe a senha.").max(200),
});

export const signupSchema = credentialsSchema.extend({
  nome: z.string().trim().min(2, "Informe seu nome completo.").max(120),
});

export const codeSchema = z.object({
  code: z.string().trim().regex(/^\d{6}$/, "O código tem 6 dígitos."),
});
