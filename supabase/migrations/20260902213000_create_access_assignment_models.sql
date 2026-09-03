-- =====================================================================
-- LinkAI: modelos reutilizáveis e histórico de atribuições internas
-- =====================================================================

CREATE TABLE IF NOT EXISTS public.linkai_acesso_modelos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id integer NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
  nome text NOT NULL CHECK (char_length(btrim(nome)) BETWEEN 2 AND 100),
  descricao text NOT NULL DEFAULT '',
  perfil_codigo text NOT NULL REFERENCES public.linkai_perfis_internos(codigo),
  two_factor_policy text NOT NULL DEFAULT 'required'
    CHECK (two_factor_policy IN ('required', 'optional', 'disabled')),
  ativo boolean NOT NULL DEFAULT true,
  criado_por uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS linkai_acesso_modelos_nome_uniq
  ON public.linkai_acesso_modelos (empresa_id, lower(nome))
  WHERE ativo;
CREATE INDEX IF NOT EXISTS linkai_acesso_modelos_empresa_idx
  ON public.linkai_acesso_modelos (empresa_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.linkai_acesso_modelo_obras (
  modelo_id uuid NOT NULL REFERENCES public.linkai_acesso_modelos(id) ON DELETE CASCADE,
  obra_id uuid NOT NULL REFERENCES public.linkai_obras(id) ON DELETE CASCADE,
  perfil_codigo text NOT NULL REFERENCES public.linkai_perfis_internos(codigo),
  principal boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (modelo_id, obra_id)
);

CREATE INDEX IF NOT EXISTS linkai_acesso_modelo_obras_obra_idx
  ON public.linkai_acesso_modelo_obras (obra_id);

CREATE TABLE IF NOT EXISTS public.linkai_acesso_modelo_permissoes (
  modelo_id uuid NOT NULL REFERENCES public.linkai_acesso_modelos(id) ON DELETE CASCADE,
  permissao_codigo text NOT NULL REFERENCES public.linkai_permissoes(codigo) ON DELETE CASCADE,
  concedida boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (modelo_id, permissao_codigo)
);

CREATE TABLE IF NOT EXISTS public.linkai_acesso_historico (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id integer NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
  usuario_id integer REFERENCES public.usuarios(id) ON DELETE SET NULL,
  convite_id uuid REFERENCES public.linkai_user_convites(id) ON DELETE SET NULL,
  modelo_id uuid REFERENCES public.linkai_acesso_modelos(id) ON DELETE SET NULL,
  actor_user_id uuid,
  actor_usuario_id integer REFERENCES public.usuarios(id) ON DELETE SET NULL,
  acao text NOT NULL CHECK (acao IN ('acessos_atualizados', 'convite_criado', 'modelo_criado', 'modelo_aplicado')),
  snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS linkai_acesso_historico_empresa_idx
  ON public.linkai_acesso_historico (empresa_id, created_at DESC);
CREATE INDEX IF NOT EXISTS linkai_acesso_historico_usuario_idx
  ON public.linkai_acesso_historico (usuario_id, created_at DESC);

DROP TRIGGER IF EXISTS linkai_acesso_modelos_updated_at ON public.linkai_acesso_modelos;
CREATE TRIGGER linkai_acesso_modelos_updated_at
  BEFORE UPDATE ON public.linkai_acesso_modelos
  FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();

GRANT SELECT ON public.linkai_acesso_modelos TO authenticated;
GRANT SELECT ON public.linkai_acesso_modelo_obras TO authenticated;
GRANT SELECT ON public.linkai_acesso_modelo_permissoes TO authenticated;
GRANT SELECT ON public.linkai_acesso_historico TO authenticated;
GRANT ALL ON public.linkai_acesso_modelos TO service_role;
GRANT ALL ON public.linkai_acesso_modelo_obras TO service_role;
GRANT ALL ON public.linkai_acesso_modelo_permissoes TO service_role;
GRANT ALL ON public.linkai_acesso_historico TO service_role;

ALTER TABLE public.linkai_acesso_modelos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.linkai_acesso_modelo_obras ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.linkai_acesso_modelo_permissoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.linkai_acesso_historico ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS linkai_acesso_modelos_select ON public.linkai_acesso_modelos;
CREATE POLICY linkai_acesso_modelos_select ON public.linkai_acesso_modelos
  FOR SELECT TO authenticated
  USING (public.linkai_can_manage_empresa(empresa_id));

DROP POLICY IF EXISTS linkai_acesso_modelos_update ON public.linkai_acesso_modelos;
CREATE POLICY linkai_acesso_modelos_update ON public.linkai_acesso_modelos
  FOR UPDATE TO authenticated
  USING (public.linkai_can_manage_empresa(empresa_id))
  WITH CHECK (public.linkai_can_manage_empresa(empresa_id));

DROP POLICY IF EXISTS linkai_acesso_modelos_service ON public.linkai_acesso_modelos;
CREATE POLICY linkai_acesso_modelos_service ON public.linkai_acesso_modelos
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS linkai_acesso_modelo_obras_select ON public.linkai_acesso_modelo_obras;
CREATE POLICY linkai_acesso_modelo_obras_select ON public.linkai_acesso_modelo_obras
  FOR SELECT TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.linkai_acesso_modelos m
     WHERE m.id = modelo_id AND public.linkai_can_manage_empresa(m.empresa_id)
  ));

DROP POLICY IF EXISTS linkai_acesso_modelo_obras_service ON public.linkai_acesso_modelo_obras;
CREATE POLICY linkai_acesso_modelo_obras_service ON public.linkai_acesso_modelo_obras
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS linkai_acesso_modelo_permissoes_select ON public.linkai_acesso_modelo_permissoes;
CREATE POLICY linkai_acesso_modelo_permissoes_select ON public.linkai_acesso_modelo_permissoes
  FOR SELECT TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.linkai_acesso_modelos m
     WHERE m.id = modelo_id AND public.linkai_can_manage_empresa(m.empresa_id)
  ));

DROP POLICY IF EXISTS linkai_acesso_modelo_permissoes_service ON public.linkai_acesso_modelo_permissoes;
CREATE POLICY linkai_acesso_modelo_permissoes_service ON public.linkai_acesso_modelo_permissoes
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS linkai_acesso_historico_select ON public.linkai_acesso_historico;
CREATE POLICY linkai_acesso_historico_select ON public.linkai_acesso_historico
  FOR SELECT TO authenticated
  USING (public.linkai_can_manage_empresa(empresa_id));

DROP POLICY IF EXISTS linkai_acesso_historico_service ON public.linkai_acesso_historico;
CREATE POLICY linkai_acesso_historico_service ON public.linkai_acesso_historico
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Registra uma alteração feita pelo usuário autenticado sem permitir que o
-- cliente escolha o ator. O snapshot contém somente configuração de acesso.
CREATE OR REPLACE FUNCTION public.linkai_record_access_history(
  p_empresa_id integer,
  p_acao text,
  p_usuario_id integer DEFAULT NULL,
  p_convite_id uuid DEFAULT NULL,
  p_modelo_id uuid DEFAULT NULL,
  p_snapshot jsonb DEFAULT '{}'::jsonb
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
  v_id uuid;
  v_actor_usuario_id integer;
BEGIN
  IF p_acao NOT IN ('acessos_atualizados', 'convite_criado', 'modelo_criado', 'modelo_aplicado') THEN
    RAISE EXCEPTION 'Ação de histórico inválida.' USING ERRCODE = '22023';
  END IF;
  IF NOT public.linkai_can_manage_empresa(p_empresa_id) THEN
    RAISE EXCEPTION 'Permissão insuficiente para registrar histórico.' USING ERRCODE = '42501';
  END IF;

  SELECT id INTO v_actor_usuario_id
    FROM public.usuarios
   WHERE auth_user_id = auth.uid()
   LIMIT 1;

  INSERT INTO public.linkai_acesso_historico (
    empresa_id, usuario_id, convite_id, modelo_id, actor_user_id, actor_usuario_id,
    acao, snapshot
  ) VALUES (
    p_empresa_id, p_usuario_id, p_convite_id, p_modelo_id, auth.uid(), v_actor_usuario_id,
    p_acao, COALESCE(p_snapshot, '{}'::jsonb)
  )
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$function$;

REVOKE ALL ON FUNCTION public.linkai_record_access_history(integer, text, integer, uuid, uuid, jsonb) FROM public;
GRANT EXECUTE ON FUNCTION public.linkai_record_access_history(integer, text, integer, uuid, uuid, jsonb)
  TO authenticated, service_role;

-- Cria um modelo completo em uma única operação, validando escopo, função e obras.
CREATE OR REPLACE FUNCTION public.linkai_create_access_model(
  p_empresa_id integer,
  p_nome text,
  p_descricao text,
  p_perfil_codigo text,
  p_two_factor_policy text,
  p_obras jsonb DEFAULT '[]'::jsonb,
  p_permissoes jsonb DEFAULT '[]'::jsonb
)
RETURNS public.linkai_acesso_modelos
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
  v_model public.linkai_acesso_modelos;
  v_item jsonb;
  v_obra public.linkai_obras;
  v_perfil text;
  v_principal uuid;
BEGIN
  IF NOT public.linkai_can_manage_empresa(p_empresa_id) THEN
    RAISE EXCEPTION 'Permissão insuficiente para criar modelo.' USING ERRCODE = '42501';
  END IF;
  IF p_nome IS NULL OR char_length(btrim(p_nome)) < 2 THEN
    RAISE EXCEPTION 'Informe um nome para o modelo.' USING ERRCODE = '22023';
  END IF;
  IF p_perfil_codigo = 'superadmin_2lock' THEN
    RAISE EXCEPTION 'O perfil Superadmin 2LOCK não pode ser salvo em um modelo de empresa.'
      USING ERRCODE = '22023';
  END IF;
  IF p_two_factor_policy NOT IN ('required', 'optional', 'disabled') THEN
    RAISE EXCEPTION 'Política de 2FA inválida.' USING ERRCODE = '22023';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM public.linkai_perfis_internos
     WHERE codigo = p_perfil_codigo AND ativo
  ) THEN
    RAISE EXCEPTION 'Função inválida.' USING ERRCODE = '22023';
  END IF;
  IF jsonb_typeof(p_obras) <> 'array' OR jsonb_array_length(p_obras) = 0 THEN
    RAISE EXCEPTION 'Selecione ao menos uma obra.' USING ERRCODE = '22023';
  END IF;

  SELECT (item ->> 'obra_id')::uuid INTO v_principal
    FROM jsonb_array_elements(p_obras) item
   WHERE COALESCE((item ->> 'principal')::boolean, false)
   LIMIT 1;
  IF v_principal IS NULL THEN
    v_principal := ((p_obras -> 0) ->> 'obra_id')::uuid;
  END IF;

  INSERT INTO public.linkai_acesso_modelos (
    empresa_id, nome, descricao, perfil_codigo, two_factor_policy, criado_por
  ) VALUES (
    p_empresa_id, btrim(p_nome), COALESCE(btrim(p_descricao), ''), p_perfil_codigo,
    p_two_factor_policy, auth.uid()
  ) RETURNING * INTO v_model;

  FOR v_item IN SELECT * FROM jsonb_array_elements(p_obras) LOOP
    v_perfil := COALESCE(NULLIF(v_item ->> 'perfil_codigo', ''), p_perfil_codigo);
    SELECT * INTO v_obra FROM public.linkai_obras WHERE id = (v_item ->> 'obra_id')::uuid;
    IF NOT FOUND OR v_obra.empresa_id <> p_empresa_id OR NOT v_obra.ativo THEN
      RAISE EXCEPTION 'Obra inválida para este modelo.' USING ERRCODE = '22023';
    END IF;
    IF v_perfil = 'superadmin_2lock' OR NOT EXISTS (
      SELECT 1 FROM public.linkai_perfis_internos WHERE codigo = v_perfil AND ativo
    ) THEN
      RAISE EXCEPTION 'Função inválida para a obra.' USING ERRCODE = '22023';
    END IF;
    IF v_perfil = 'supervisor_empresa' AND v_obra.tipo <> 'escritorio' THEN
      RAISE EXCEPTION 'Supervisor da empresa só pode ser atribuído ao ESCRITORIO.'
        USING ERRCODE = '22023';
    END IF;

    INSERT INTO public.linkai_acesso_modelo_obras (modelo_id, obra_id, perfil_codigo, principal)
    VALUES (v_model.id, v_obra.id, v_perfil, v_obra.id = v_principal);
  END LOOP;

  IF jsonb_typeof(p_permissoes) = 'array' THEN
    INSERT INTO public.linkai_acesso_modelo_permissoes (modelo_id, permissao_codigo, concedida)
    SELECT v_model.id, item ->> 'permissao_codigo', COALESCE((item ->> 'concedida')::boolean, true)
      FROM jsonb_array_elements(p_permissoes) item
     WHERE EXISTS (
       SELECT 1 FROM public.linkai_permissoes p WHERE p.codigo = item ->> 'permissao_codigo'
     )
    ON CONFLICT (modelo_id, permissao_codigo)
    DO UPDATE SET concedida = EXCLUDED.concedida;
  END IF;

  INSERT INTO public.linkai_acesso_historico (
    empresa_id, modelo_id, actor_user_id, actor_usuario_id, acao, snapshot
  ) VALUES (
    p_empresa_id, v_model.id, auth.uid(), public.linkai_current_usuario_id(), 'modelo_criado',
    jsonb_build_object(
      'modelo_nome', v_model.nome,
      'perfil_codigo', p_perfil_codigo,
      'two_factor_policy', p_two_factor_policy,
      'obras', p_obras,
      'permissoes', p_permissoes
    )
  );

  RETURN v_model;
END;
$function$;

REVOKE ALL ON FUNCTION public.linkai_create_access_model(integer, text, text, text, text, jsonb, jsonb) FROM public;
GRANT EXECUTE ON FUNCTION public.linkai_create_access_model(integer, text, text, text, text, jsonb, jsonb)
  TO authenticated, service_role;

-- Aplica o modelo diretamente a um usuário, sem exigir que o operador repita o preenchimento.
CREATE OR REPLACE FUNCTION public.linkai_apply_access_model(
  p_modelo_id uuid,
  p_usuario_id integer
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
  v_model public.linkai_acesso_modelos;
  v_usuario public.usuarios;
  v_obras jsonb;
  v_permissoes jsonb;
BEGIN
  SELECT * INTO v_model
    FROM public.linkai_acesso_modelos
   WHERE id = p_modelo_id AND ativo
   FOR SHARE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Modelo não encontrado ou inativo.' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_usuario FROM public.usuarios WHERE id = p_usuario_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Usuário não encontrado.' USING ERRCODE = '22023';
  END IF;
  IF v_usuario.empresa_id IS NULL
     OR v_usuario.empresa_id <> v_model.empresa_id
     OR NOT public.linkai_can_manage_empresa(v_model.empresa_id) THEN
    RAISE EXCEPTION 'Permissão insuficiente para aplicar este modelo.' USING ERRCODE = '42501';
  END IF;

  SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'obra_id', mo.obra_id,
      'perfil_codigo', mo.perfil_codigo,
      'principal', mo.principal
    ) ORDER BY mo.principal DESC, mo.created_at), '[]'::jsonb)
    INTO v_obras
    FROM public.linkai_acesso_modelo_obras mo
   WHERE mo.modelo_id = v_model.id;

  SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'permissao_codigo', mp.permissao_codigo,
      'concedida', mp.concedida
    ) ORDER BY mp.permissao_codigo), '[]'::jsonb)
    INTO v_permissoes
    FROM public.linkai_acesso_modelo_permissoes mp
   WHERE mp.modelo_id = v_model.id;

  PERFORM public.linkai_set_usuario_acessos(
    p_usuario_id, v_obras, v_permissoes, v_model.two_factor_policy, NULL
  );

  INSERT INTO public.linkai_acesso_historico (
    empresa_id, usuario_id, modelo_id, actor_user_id, actor_usuario_id, acao, snapshot
  ) VALUES (
    v_model.empresa_id, v_usuario.id, v_model.id, auth.uid(), public.linkai_current_usuario_id(),
    'modelo_aplicado', jsonb_build_object(
      'modelo_nome', v_model.nome,
      'usuario_nome', v_usuario.nome,
      'usuario_email', v_usuario.email,
      'perfil_codigo', v_model.perfil_codigo,
      'two_factor_policy', v_model.two_factor_policy,
      'obras', v_obras,
      'permissoes', v_permissoes
    )
  );
END;
$function$;

REVOKE ALL ON FUNCTION public.linkai_apply_access_model(uuid, integer) FROM public;
GRANT EXECUTE ON FUNCTION public.linkai_apply_access_model(uuid, integer) TO authenticated, service_role;

REVOKE ALL ON public.linkai_acesso_modelos, public.linkai_acesso_modelo_obras,
  public.linkai_acesso_modelo_permissoes, public.linkai_acesso_historico FROM anon;
