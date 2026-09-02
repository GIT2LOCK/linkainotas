-- 1) Overrides de permissão por usuário
CREATE TABLE IF NOT EXISTS public.linkai_usuario_permissoes (
  usuario_id integer NOT NULL REFERENCES public.usuarios(id) ON DELETE CASCADE,
  permissao_codigo text NOT NULL REFERENCES public.linkai_permissoes(codigo) ON DELETE CASCADE,
  concedida boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (usuario_id, permissao_codigo)
);

GRANT SELECT ON public.linkai_usuario_permissoes TO authenticated;
GRANT ALL ON public.linkai_usuario_permissoes TO service_role;
ALTER TABLE public.linkai_usuario_permissoes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "usuario_permissoes_select" ON public.linkai_usuario_permissoes;
CREATE POLICY "usuario_permissoes_select" ON public.linkai_usuario_permissoes
  FOR SELECT TO authenticated
  USING (
    usuario_id = public.linkai_current_usuario_id()
    OR EXISTS (
      SELECT 1 FROM public.usuarios u
       WHERE u.id = linkai_usuario_permissoes.usuario_id
         AND public.linkai_can_manage_empresa(u.empresa_id)
    )
  );

-- 2) Pré-cadastro: obras e permissões personalizadas
CREATE TABLE IF NOT EXISTS public.linkai_convite_obras (
  convite_id uuid NOT NULL REFERENCES public.linkai_user_convites(id) ON DELETE CASCADE,
  obra_id uuid NOT NULL REFERENCES public.linkai_obras(id) ON DELETE CASCADE,
  perfil_codigo text NOT NULL REFERENCES public.linkai_perfis_internos(codigo),
  principal boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (convite_id, obra_id)
);

CREATE TABLE IF NOT EXISTS public.linkai_convite_permissoes (
  convite_id uuid NOT NULL REFERENCES public.linkai_user_convites(id) ON DELETE CASCADE,
  permissao_codigo text NOT NULL REFERENCES public.linkai_permissoes(codigo) ON DELETE CASCADE,
  concedida boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (convite_id, permissao_codigo)
);

GRANT SELECT ON public.linkai_convite_obras TO authenticated;
GRANT SELECT ON public.linkai_convite_permissoes TO authenticated;
GRANT ALL ON public.linkai_convite_obras TO service_role;
GRANT ALL ON public.linkai_convite_permissoes TO service_role;
ALTER TABLE public.linkai_convite_obras ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.linkai_convite_permissoes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "convite_obras_select" ON public.linkai_convite_obras;
CREATE POLICY "convite_obras_select" ON public.linkai_convite_obras
  FOR SELECT TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.linkai_user_convites c
     WHERE c.id = linkai_convite_obras.convite_id
       AND public.linkai_can_manage_empresa(c.empresa_id)
  ));

DROP POLICY IF EXISTS "convite_permissoes_select" ON public.linkai_convite_permissoes;
CREATE POLICY "convite_permissoes_select" ON public.linkai_convite_permissoes
  FOR SELECT TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.linkai_user_convites c
     WHERE c.id = linkai_convite_permissoes.convite_id
       AND public.linkai_can_manage_empresa(c.empresa_id)
  ));

-- 3) Permissão efetiva = override individual, senão permissão da função
CREATE OR REPLACE FUNCTION public.linkai_has_permissao(_permissao text)
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path TO 'public'
AS $function$
  SELECT public.linkai_is_platform_superadmin() OR COALESCE(
    (SELECT up.concedida
       FROM public.linkai_usuario_permissoes up
       JOIN public.usuarios u ON u.id = up.usuario_id
      WHERE u.auth_user_id = auth.uid() AND u.ativo
        AND up.permissao_codigo = _permissao
      LIMIT 1),
    EXISTS (
      SELECT 1 FROM public.linkai_usuario_obras uo
        JOIN public.usuarios u ON u.id = uo.usuario_id
        JOIN public.linkai_perfil_permissoes pp ON pp.perfil_codigo = uo.perfil_codigo
       WHERE u.auth_user_id = auth.uid() AND u.ativo AND uo.ativo
         AND pp.permissao_codigo = _permissao
    )
  )
$function$;

-- 4) Editar acessos de um usuário existente (obras múltiplas + overrides)
CREATE OR REPLACE FUNCTION public.linkai_set_usuario_acessos(
  p_usuario_id integer,
  p_obras jsonb DEFAULT '[]'::jsonb,
  p_permissoes jsonb DEFAULT NULL,
  p_two_factor_policy text DEFAULT NULL,
  p_ativo boolean DEFAULT NULL
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
  v_usuario public.usuarios;
  v_item jsonb;
  v_obra_ids uuid[] := ARRAY[]::uuid[];
  v_is_service boolean := (current_setting('request.jwt.claims', true) IS NULL);
BEGIN
  SELECT * INTO v_usuario FROM public.usuarios WHERE id = p_usuario_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Usuário não encontrado.' USING ERRCODE = '22023'; END IF;

  IF NOT v_is_service AND auth.uid() IS NOT NULL THEN
    IF NOT public.linkai_can_manage_empresa(v_usuario.empresa_id) THEN
      RAISE EXCEPTION 'Permissão insuficiente para administrar acessos desta empresa.'
        USING ERRCODE = '42501';
    END IF;
  END IF;

  IF p_two_factor_policy IS NOT NULL THEN
    IF p_two_factor_policy NOT IN ('required', 'optional', 'disabled') THEN
      RAISE EXCEPTION 'Política de 2FA inválida.' USING ERRCODE = '22023';
    END IF;
    UPDATE public.usuarios
       SET two_factor_policy = p_two_factor_policy, atualizado_em = now()
     WHERE id = p_usuario_id;
  END IF;

  IF p_ativo IS NOT NULL THEN
    UPDATE public.usuarios SET ativo = p_ativo, atualizado_em = now() WHERE id = p_usuario_id;
  END IF;

  IF p_obras IS NOT NULL AND jsonb_typeof(p_obras) = 'array' AND jsonb_array_length(p_obras) > 0 THEN
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_obras) LOOP
      PERFORM public.linkai_assign_user_to_obra(
        p_usuario_id,
        (v_item ->> 'obra_id')::uuid,
        v_item ->> 'perfil_codigo',
        COALESCE((v_item ->> 'principal')::boolean, false)
      );
      v_obra_ids := v_obra_ids || (v_item ->> 'obra_id')::uuid;
    END LOOP;

    UPDATE public.linkai_usuario_obras
       SET ativo = false, principal = false, updated_at = now()
     WHERE usuario_id = p_usuario_id
       AND ativo
       AND NOT (obra_id = ANY (v_obra_ids));
  END IF;

  IF p_permissoes IS NOT NULL AND jsonb_typeof(p_permissoes) = 'array' THEN
    DELETE FROM public.linkai_usuario_permissoes WHERE usuario_id = p_usuario_id;
    INSERT INTO public.linkai_usuario_permissoes (usuario_id, permissao_codigo, concedida)
    SELECT p_usuario_id, item ->> 'permissao_codigo', COALESCE((item ->> 'concedida')::boolean, true)
      FROM jsonb_array_elements(p_permissoes) AS item
     WHERE EXISTS (
       SELECT 1 FROM public.linkai_permissoes pm WHERE pm.codigo = item ->> 'permissao_codigo'
     )
    ON CONFLICT (usuario_id, permissao_codigo)
    DO UPDATE SET concedida = EXCLUDED.concedida, updated_at = now();
  END IF;
END;
$function$;

REVOKE ALL ON FUNCTION public.linkai_set_usuario_acessos(integer, jsonb, jsonb, text, boolean) FROM public;
GRANT EXECUTE ON FUNCTION public.linkai_set_usuario_acessos(integer, jsonb, jsonb, text, boolean) TO authenticated, service_role;

-- 5) Criar pré-cadastro completo
CREATE OR REPLACE FUNCTION public.linkai_create_convite(
  p_nome text,
  p_email text,
  p_perfil_codigo text,
  p_two_factor_policy text,
  p_obras jsonb DEFAULT '[]'::jsonb,
  p_permissoes jsonb DEFAULT '[]'::jsonb
)
RETURNS public.linkai_user_convites
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
  v_empresa_id integer := public.linkai_current_empresa_id();
  v_convite public.linkai_user_convites;
  v_item jsonb;
  v_obra public.linkai_obras;
  v_principal uuid;
BEGIN
  IF p_two_factor_policy NOT IN ('required', 'optional', 'disabled') THEN
    RAISE EXCEPTION 'Política de 2FA inválida.' USING ERRCODE = '22023';
  END IF;
  IF jsonb_typeof(p_obras) <> 'array' OR jsonb_array_length(p_obras) = 0 THEN
    RAISE EXCEPTION 'Selecione ao menos uma obra.' USING ERRCODE = '22023';
  END IF;

  -- Superadmin de plataforma pode agir na empresa das obras informadas.
  IF v_empresa_id IS NULL THEN
    SELECT o.empresa_id INTO v_empresa_id
      FROM public.linkai_obras o
     WHERE o.id = ((p_obras -> 0) ->> 'obra_id')::uuid;
  END IF;

  IF NOT public.linkai_can_manage_empresa(v_empresa_id) THEN
    RAISE EXCEPTION 'Permissão insuficiente para administrar acessos desta empresa.'
      USING ERRCODE = '42501';
  END IF;

  SELECT COALESCE(
      (SELECT (v_item ->> 'obra_id')::uuid FROM jsonb_array_elements(p_obras) AS v_item
        WHERE COALESCE((v_item ->> 'principal')::boolean, false) LIMIT 1),
      ((p_obras -> 0) ->> 'obra_id')::uuid)
    INTO v_principal;

  INSERT INTO public.linkai_user_convites (
    nome, email, empresa_id, obra_id, perfil_codigo, two_factor_policy, status, criado_por
  ) VALUES (
    p_nome, lower(p_email), v_empresa_id, v_principal, p_perfil_codigo, p_two_factor_policy,
    'pending', auth.uid()
  )
  RETURNING * INTO v_convite;

  FOR v_item IN SELECT * FROM jsonb_array_elements(p_obras) LOOP
    SELECT * INTO v_obra FROM public.linkai_obras WHERE id = (v_item ->> 'obra_id')::uuid;
    IF NOT FOUND OR v_obra.empresa_id <> v_empresa_id THEN
      RAISE EXCEPTION 'Obra inválida para esta empresa.' USING ERRCODE = '22023';
    END IF;

    INSERT INTO public.linkai_convite_obras (convite_id, obra_id, perfil_codigo, principal)
    VALUES (
      v_convite.id,
      v_obra.id,
      COALESCE(NULLIF(v_item ->> 'perfil_codigo', ''), p_perfil_codigo),
      v_obra.id = v_principal
    )
    ON CONFLICT (convite_id, obra_id) DO NOTHING;
  END LOOP;

  IF jsonb_typeof(p_permissoes) = 'array' THEN
    INSERT INTO public.linkai_convite_permissoes (convite_id, permissao_codigo, concedida)
    SELECT v_convite.id, item ->> 'permissao_codigo', COALESCE((item ->> 'concedida')::boolean, true)
      FROM jsonb_array_elements(p_permissoes) AS item
     WHERE EXISTS (
       SELECT 1 FROM public.linkai_permissoes pm WHERE pm.codigo = item ->> 'permissao_codigo'
     )
    ON CONFLICT (convite_id, permissao_codigo) DO UPDATE SET concedida = EXCLUDED.concedida;
  END IF;

  RETURN v_convite;
END;
$function$;

REVOKE ALL ON FUNCTION public.linkai_create_convite(text, text, text, text, jsonb, jsonb) FROM public;
GRANT EXECUTE ON FUNCTION public.linkai_create_convite(text, text, text, text, jsonb, jsonb) TO authenticated, service_role;

-- 6) Vínculo no primeiro acesso aplica todas as obras e overrides do pré-cadastro
CREATE OR REPLACE FUNCTION public.linkai_link_convite(p_email text)
RETURNS public.linkai_user_convites
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
  v_convite public.linkai_user_convites;
  v_usuario public.usuarios;
  v_obra uuid;
  v_row record;
  v_count integer := 0;
BEGIN
  SELECT * INTO v_convite FROM public.linkai_user_convites
   WHERE lower(email) = lower(p_email) AND status = 'pending' FOR UPDATE;
  IF NOT FOUND THEN RETURN NULL; END IF;

  SELECT * INTO v_usuario FROM public.usuarios WHERE lower(email) = lower(p_email) FOR UPDATE;
  IF NOT FOUND THEN RETURN NULL; END IF;

  UPDATE public.usuarios
     SET empresa_id = v_convite.empresa_id,
         two_factor_policy = v_convite.two_factor_policy,
         atualizado_em = now()
   WHERE id = v_usuario.id;

  IF v_convite.perfil_codigo <> 'superadmin_2lock' THEN
    FOR v_row IN
      SELECT co.obra_id, co.perfil_codigo, co.principal
        FROM public.linkai_convite_obras co
       WHERE co.convite_id = v_convite.id
       ORDER BY co.principal DESC
    LOOP
      PERFORM public.linkai_assign_user_to_obra(
        v_usuario.id, v_row.obra_id, v_row.perfil_codigo, v_row.principal
      );
      v_count := v_count + 1;
    END LOOP;

    IF v_count = 0 THEN
      v_obra := COALESCE(v_convite.obra_id, public.linkai_ensure_escritorio(v_convite.empresa_id));
      PERFORM public.linkai_assign_user_to_obra(v_usuario.id, v_obra, v_convite.perfil_codigo, true);
    END IF;
  END IF;

  INSERT INTO public.linkai_usuario_permissoes (usuario_id, permissao_codigo, concedida)
  SELECT v_usuario.id, cp.permissao_codigo, cp.concedida
    FROM public.linkai_convite_permissoes cp
   WHERE cp.convite_id = v_convite.id
  ON CONFLICT (usuario_id, permissao_codigo)
  DO UPDATE SET concedida = EXCLUDED.concedida, updated_at = now();

  UPDATE public.linkai_user_convites
     SET status = 'linked', vinculado_em = now()
   WHERE id = v_convite.id
  RETURNING * INTO v_convite;

  RETURN v_convite;
END;
$function$;