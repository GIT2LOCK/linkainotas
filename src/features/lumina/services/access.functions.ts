/**
 * Server functions do controle interno de acessos do LinkAI.
 *
 * Todas usam o cliente autenticado (RLS como o usuário-espelho) e revalidam
 * as permissões internas no servidor — o frontend nunca é a única barreira.
 */
import { createServerFn } from "@tanstack/react-start";
import type { SupabaseClient } from "@supabase/supabase-js";

import { requireLinkaiUser } from "@/lib/auth/require-user";
import type { Database } from "@/integrations/supabase/types";

type AuthedClient = SupabaseClient<Database>;

export type ObraItem = {
  id: string;
  codigo: string;
  nome: string;
  tipo: string;
  ativo: boolean;
  empresaId: number;
  empresaNome: string | null;
  createdAt: string;
};


export type UsuarioObraVinculo = {
  obraId: string;
  obraNome: string;
  obraTipo: string;
  perfilCodigo: string;
  principal: boolean;
};

export type UsuarioItem = {
  id: number;
  nome: string;
  email: string;
  ativo: boolean;
  twoFactorPolicy: string;
  isPlatformSuperadmin: boolean;
  obraNome: string | null;
  obraId: string | null;
  perfilCodigo: string | null;
  obras: UsuarioObraVinculo[];
  overrides: { permissaoCodigo: string; concedida: boolean }[];
};

export type ConviteItem = {
  id: string;
  nome: string;
  email: string;
  obraNome: string | null;
  perfilCodigo: string;
  twoFactorPolicy: string;
  status: string;
  criadoEm: string;
};


export type PerfilItem = {
  codigo: string;
  nome: string;
  escopo: string;
  nivel: number;
  permissoes: string[];
};

export type PermissaoItem = { codigo: string; nome: string };

export type AtividadeItem = {
  id: string;
  usuario: string | null;
  email: string | null;
  obra: string | null;
  acao: string;
  status: string;
  arquivos: string | null;
  mensagem: string | null;
  createdAt: string;
};

const TWO_FACTOR = ["required", "optional", "disabled"] as const;

async function assertPermissao(supabase: AuthedClient, permissao: string) {
  const { data } = await supabase.rpc("linkai_has_permissao", { _permissao: permissao });
  if (data !== true) throw new Response("Forbidden", { status: 403 });
}

function str(value: unknown, field: string, max = 180): string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`Campo obrigatório: ${field}.`);
  }
  return value.trim().slice(0, max);
}

/** Obras visíveis para o usuário (RLS escopa por empresa/atribuição). */
export const listObras = createServerFn({ method: "GET" })
  .middleware([requireLinkaiUser])
  .handler(async ({ context }): Promise<ObraItem[]> => {
    const { data, error } = await context.supabase
      .from("linkai_obras")
      .select("id, codigo, nome, tipo, ativo, empresa_id, created_at, empresa:empresas(nome_fantasia)")
      .order("tipo", { ascending: true })
      .order("codigo", { ascending: true });

    if (error) throw error;

    return (data ?? []).map((row) => ({
      id: row.id,
      codigo: row.codigo,
      nome: row.nome,
      tipo: row.tipo,
      ativo: row.ativo,
      empresaId: row.empresa_id,
      empresaNome: (row.empresa as { nome_fantasia: string } | null)?.nome_fantasia ?? null,
      createdAt: row.created_at,
    }));

  });

export const createObra = createServerFn({ method: "POST" })
  .middleware([requireLinkaiUser])
  .validator((data: { codigo: string; nome: string }) => ({
    codigo: str(data?.codigo, "código", 40).toUpperCase(),
    nome: str(data?.nome, "nome"),
  }))
  .handler(async ({ context, data }): Promise<ObraItem> => {
    await assertPermissao(context.supabase, "works.manage");

    if (data.codigo === "ESCRITORIO") {
      throw new Error("O ESCRITORIO é criado automaticamente e não pode ser duplicado.");
    }
    if (!context.user.empresaId) {
      throw new Error("Usuário sem empresa vinculada.");
    }

    const { data: row, error } = await context.supabase.rpc("linkai_create_obra", {
      p_empresa_id: context.user.empresaId,
      p_codigo: data.codigo,
      p_nome: data.nome,
      p_tipo: "obra",
    });

    if (error) throw new Error(error.message);
    const obra = (Array.isArray(row) ? row[0] : row) as ObraItem & {
      empresa_id: number;
      created_at: string;
    };

    return {
      id: obra.id,
      codigo: obra.codigo,
      nome: obra.nome,
      tipo: obra.tipo,
      ativo: obra.ativo,
      empresaId: obra.empresa_id,
      empresaNome: null,
      createdAt: obra.created_at,

    };
  });

/** Usuários da empresa com obra/função principal. */
export const listUsuarios = createServerFn({ method: "GET" })
  .middleware([requireLinkaiUser])
  .handler(async ({ context }): Promise<UsuarioItem[]> => {
    await assertPermissao(context.supabase, "access.manage");

    const { data, error } = await context.supabase
      .from("usuarios")
      .select("id, nome, email, ativo, two_factor_policy, is_platform_superadmin")
      .order("nome", { ascending: true });

    if (error) throw error;

    const { data: vinculos } = await context.supabase
      .from("linkai_usuario_obras")
      .select("usuario_id, perfil_codigo, principal, obra:linkai_obras(id, nome, tipo)")
      .eq("ativo", true)
      .order("principal", { ascending: false });

    const { data: overrides } = await context.supabase
      .from("linkai_usuario_permissoes")
      .select("usuario_id, permissao_codigo, concedida");

    const byUser = new Map<number, UsuarioObraVinculo[]>();
    for (const row of vinculos ?? []) {
      const obra = row.obra as { id: string; nome: string; tipo: string } | null;
      if (!obra) continue;
      const list = byUser.get(row.usuario_id) ?? [];
      list.push({
        obraId: obra.id,
        obraNome: obra.nome,
        obraTipo: obra.tipo,
        perfilCodigo: row.perfil_codigo,
        principal: row.principal === true,
      });
      byUser.set(row.usuario_id, list);
    }

    const overridesByUser = new Map<number, { permissaoCodigo: string; concedida: boolean }[]>();
    for (const row of overrides ?? []) {
      const list = overridesByUser.get(row.usuario_id) ?? [];
      list.push({ permissaoCodigo: row.permissao_codigo, concedida: row.concedida });
      overridesByUser.set(row.usuario_id, list);
    }

    return (data ?? []).map((row) => {
      const obras = byUser.get(row.id) ?? [];
      const principal = obras.find((item) => item.principal) ?? obras[0];
      return {
        id: row.id,
        nome: row.nome,
        email: row.email,
        ativo: row.ativo !== false,
        twoFactorPolicy: row.two_factor_policy,
        isPlatformSuperadmin: row.is_platform_superadmin,
        obraId: principal?.obraId ?? null,
        obraNome: obras.length > 1
          ? `${principal?.obraNome ?? "-"} +${obras.length - 1}`
          : (principal?.obraNome ?? null),
        perfilCodigo: principal?.perfilCodigo ?? null,
        obras,
        overrides: overridesByUser.get(row.id) ?? [],
      };
    });

  });

export const listConvites = createServerFn({ method: "GET" })
  .middleware([requireLinkaiUser])
  .handler(async ({ context }): Promise<ConviteItem[]> => {
    await assertPermissao(context.supabase, "access.manage");

    const { data, error } = await context.supabase
      .from("linkai_user_convites")
      .select(
        "id, nome, email, perfil_codigo, two_factor_policy, status, criado_em, obra:linkai_obras(nome)",
      )
      .order("criado_em", { ascending: false });

    if (error) throw error;

    return (data ?? []).map((row) => ({
      id: row.id,
      nome: row.nome,
      email: row.email,
      obraNome: (row.obra as { nome: string } | null)?.nome ?? null,
      perfilCodigo: row.perfil_codigo,
      twoFactorPolicy: row.two_factor_policy,
      status: row.status,
      criadoEm: row.criado_em,
    }));
  });

export type ObraAtribuicaoInput = { obraId: string; perfilCodigo: string; principal?: boolean };
export type PermissaoOverrideInput = { permissaoCodigo: string; concedida: boolean };

function normalizeObras(value: unknown): ObraAtribuicaoInput[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error("Selecione ao menos uma obra.");
  }
  return value.map((item) => {
    const row = item as ObraAtribuicaoInput;
    return {
      obraId: str(row?.obraId, "obra", 40),
      perfilCodigo: str(row?.perfilCodigo, "função", 40),
      principal: row?.principal === true,
    };
  });
}

function normalizeOverrides(value: unknown): PermissaoOverrideInput[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    const row = item as PermissaoOverrideInput;
    return {
      permissaoCodigo: str(row?.permissaoCodigo, "permissão", 60),
      concedida: row?.concedida === true,
    };
  });
}

function toRpcObras(obras: ObraAtribuicaoInput[]) {
  return obras.map((obra) => ({
    obra_id: obra.obraId,
    perfil_codigo: obra.perfilCodigo,
    principal: obra.principal === true,
  }));
}

function toRpcPermissoes(overrides: PermissaoOverrideInput[]) {
  return overrides.map((item) => ({
    permissao_codigo: item.permissaoCodigo,
    concedida: item.concedida,
  }));
}

/** Pré-cadastro por e-mail: sem senha, vinculado no primeiro acesso. */
export const createConvite = createServerFn({ method: "POST" })
  .middleware([requireLinkaiUser])
  .validator(
    (data: {
      nome: string;
      email: string;
      perfilCodigo: string;
      twoFactorPolicy: string;
      obras: ObraAtribuicaoInput[];
      overrides?: PermissaoOverrideInput[];
    }) => {
      const policy = str(data?.twoFactorPolicy, "política de 2FA", 20);
      if (!TWO_FACTOR.includes(policy as (typeof TWO_FACTOR)[number])) {
        throw new Error("Política de 2FA inválida.");
      }
      return {
        nome: str(data?.nome, "nome"),
        email: str(data?.email, "e-mail").toLowerCase(),
        perfilCodigo: str(data?.perfilCodigo, "função", 40),
        twoFactorPolicy: policy,
        obras: normalizeObras(data?.obras),
        overrides: normalizeOverrides(data?.overrides),
      };
    },
  )
  .handler(async ({ context, data }) => {
    await assertPermissao(context.supabase, "access.manage");

    for (const obra of data.obras) {
      await assertAtribuicaoValida(context.supabase, obra.obraId, obra.perfilCodigo);
    }

    const { error } = await context.supabase.rpc("linkai_create_convite", {
      p_nome: data.nome,
      p_email: data.email,
      p_perfil_codigo: data.perfilCodigo,
      p_two_factor_policy: data.twoFactorPolicy,
      p_obras: toRpcObras(data.obras),
      p_permissoes: toRpcPermissoes(data.overrides),
    });

    if (error) throw new Error(error.message);
    return { ok: true };
  });

/** Atribui/edita as obras, o 2FA e as permissões de um usuário existente. */
export const updateUsuarioAcessos = createServerFn({ method: "POST" })
  .middleware([requireLinkaiUser])
  .validator(
    (data: {
      usuarioId: number;
      obras: ObraAtribuicaoInput[];
      overrides?: PermissaoOverrideInput[];
      twoFactorPolicy?: string | null;
      ativo?: boolean | null;
    }) => {
      if (typeof data?.usuarioId !== "number") throw new Error("Campo obrigatório: usuário.");
      const policy = data?.twoFactorPolicy ? str(data.twoFactorPolicy, "política de 2FA", 20) : null;
      if (policy && !TWO_FACTOR.includes(policy as (typeof TWO_FACTOR)[number])) {
        throw new Error("Política de 2FA inválida.");
      }
      return {
        usuarioId: data.usuarioId,
        obras: normalizeObras(data?.obras),
        overrides: normalizeOverrides(data?.overrides),
        twoFactorPolicy: policy,
        ativo: typeof data?.ativo === "boolean" ? data.ativo : null,
      };
    },
  )
  .handler(async ({ context, data }) => {
    await assertPermissao(context.supabase, "access.manage");

    for (const obra of data.obras) {
      await assertAtribuicaoValida(context.supabase, obra.obraId, obra.perfilCodigo);
    }

    const { error } = await context.supabase.rpc("linkai_set_usuario_acessos", {
      p_usuario_id: data.usuarioId,
      p_obras: toRpcObras(data.obras),
      p_permissoes: toRpcPermissoes(data.overrides),
      ...(data.twoFactorPolicy ? { p_two_factor_policy: data.twoFactorPolicy } : {}),
      ...(data.ativo === null ? {} : { p_ativo: data.ativo }),
    });

    if (error) throw new Error(error.message);
    return { ok: true };
  });


/** Regras de escopo replicadas no servidor (o banco também as impõe). */
async function assertAtribuicaoValida(
  supabase: AuthedClient,
  obraId: string,
  perfilCodigo: string,
) {
  if (perfilCodigo === "superadmin_2lock") {
    throw new Error("O perfil Superadmin 2LOCK é de plataforma e não pode ser atribuído a obra.");
  }

  const { data: obra } = await supabase
    .from("linkai_obras")
    .select("tipo")
    .eq("id", obraId)
    .maybeSingle();

  if (!obra) throw new Error("Obra não encontrada ou fora do seu escopo.");
  if (perfilCodigo === "supervisor_empresa" && obra.tipo !== "escritorio") {
    throw new Error("Supervisor da empresa só pode ser atribuído ao ESCRITORIO.");
  }
}

export const listPerfisEPermissoes = createServerFn({ method: "GET" })
  .middleware([requireLinkaiUser])
  .handler(
    async ({ context }): Promise<{ perfis: PerfilItem[]; permissoes: PermissaoItem[] }> => {
      const [perfis, permissoes, matriz] = await Promise.all([
        context.supabase
          .from("linkai_perfis_internos")
          .select("codigo, nome, escopo, nivel, ativo")
          .order("nivel", { ascending: false }),
        context.supabase.from("linkai_permissoes").select("codigo, nome").order("codigo"),
        context.supabase.from("linkai_perfil_permissoes").select("perfil_codigo, permissao_codigo"),
      ]);

      if (perfis.error) throw perfis.error;

      const byPerfil = new Map<string, string[]>();
      for (const row of matriz.data ?? []) {
        const list = byPerfil.get(row.perfil_codigo) ?? [];
        list.push(row.permissao_codigo);
        byPerfil.set(row.perfil_codigo, list);
      }

      return {
        perfis: (perfis.data ?? [])
          .filter((row) => row.ativo !== false && row.codigo !== "sem_acesso")
          .map((row) => ({
            codigo: row.codigo,
            nome: row.nome,
            escopo: row.escopo,
            nivel: row.nivel,
            permissoes: byPerfil.get(row.codigo) ?? [],
          })),
        permissoes: permissoes.data ?? [],
      };
    },
  );

/** Atividades: RLS já limita ao próprio usuário, à empresa ou às obras visíveis. */
export const listAtividades = createServerFn({ method: "GET" })
  .middleware([requireLinkaiUser])
  .handler(async ({ context }): Promise<AtividadeItem[]> => {
    const { data, error } = await context.supabase
      .from("linkai_activity_logs")
      .select("id, action, status, payload, message, created_at, obra:linkai_obras(nome)")
      .order("created_at", { ascending: false })
      .limit(200);

    if (error) throw error;

    return (data ?? []).map((row) => {
      const payload = (row.payload ?? {}) as Record<string, unknown>;
      const arquivos = payload["arquivos"] ?? payload["files"] ?? payload["file_names"];

      return {
        id: row.id,
        usuario: asText(payload["usuario"] ?? payload["nome"]),
        email: asText(payload["email"]),
        obra: (row.obra as { nome: string } | null)?.nome ?? null,
        acao: row.action,
        status: row.status,
        arquivos: Array.isArray(arquivos) ? arquivos.join(", ") : asText(arquivos),
        mensagem: row.message,
        createdAt: row.created_at,
      };
    });
  });

function asText(value: unknown): string | null {
  return typeof value === "string" || typeof value === "number" ? String(value) : null;
}
