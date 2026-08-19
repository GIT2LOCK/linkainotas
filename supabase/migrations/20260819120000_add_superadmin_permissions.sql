-- Extend company administration policies to the platform superadmin role.

DROP POLICY IF EXISTS empresas_select_own ON public.empresas;
CREATE POLICY empresas_select_own ON public.empresas
  FOR SELECT TO authenticated
  USING (
    public.jwt_has_permissao(ARRAY['superadmin'])
    OR (public.jwt_ativo() AND id = public.jwt_empresa_id())
  );

DROP POLICY IF EXISTS usuarios_select_self_or_empresa ON public.usuarios;
CREATE POLICY usuarios_select_self_or_empresa ON public.usuarios
  FOR SELECT TO authenticated
  USING (
    auth_user_id = auth.uid()
    OR public.jwt_has_permissao(ARRAY['superadmin'])
    OR (
      public.jwt_ativo()
      AND empresa_id IS NOT NULL
      AND empresa_id = public.jwt_empresa_id()
    )
  );

DROP POLICY IF EXISTS usuarios_admin_write ON public.usuarios;
CREATE POLICY usuarios_admin_write ON public.usuarios
  FOR INSERT TO authenticated
  WITH CHECK (
    public.jwt_has_permissao(ARRAY['superadmin'])
    OR (
      public.jwt_has_permissao(ARRAY['admin'])
      AND empresa_id = public.jwt_empresa_id()
    )
  );

DROP POLICY IF EXISTS usuarios_admin_update ON public.usuarios;
CREATE POLICY usuarios_admin_update ON public.usuarios
  FOR UPDATE TO authenticated
  USING (
    public.jwt_has_permissao(ARRAY['superadmin'])
    OR (
      public.jwt_has_permissao(ARRAY['admin'])
      AND empresa_id = public.jwt_empresa_id()
    )
  )
  WITH CHECK (
    public.jwt_has_permissao(ARRAY['superadmin'])
    OR (
      public.jwt_has_permissao(ARRAY['admin'])
      AND empresa_id = public.jwt_empresa_id()
    )
  );

DROP POLICY IF EXISTS usuarios_admin_delete ON public.usuarios;
CREATE POLICY usuarios_admin_delete ON public.usuarios
  FOR DELETE TO authenticated
  USING (
    public.jwt_has_permissao(ARRAY['superadmin'])
    OR (
      public.jwt_has_permissao(ARRAY['admin'])
      AND empresa_id = public.jwt_empresa_id()
    )
  );

DROP POLICY IF EXISTS pedidos_write_operador ON public.pedidos_pendentes;
CREATE POLICY pedidos_write_operador ON public.pedidos_pendentes
  FOR ALL TO authenticated
  USING (public.jwt_has_permissao(ARRAY['admin','operador','superadmin']))
  WITH CHECK (public.jwt_has_permissao(ARRAY['admin','operador','superadmin']));

DROP POLICY IF EXISTS notas_write_operador ON public.notas_processadas;
CREATE POLICY notas_write_operador ON public.notas_processadas
  FOR ALL TO authenticated
  USING (public.jwt_has_permissao(ARRAY['admin','operador','superadmin']))
  WITH CHECK (public.jwt_has_permissao(ARRAY['admin','operador','superadmin']));

DROP POLICY IF EXISTS regras_write_admin ON public.regras_imposto;
CREATE POLICY regras_write_admin ON public.regras_imposto
  FOR ALL TO authenticated
  USING (public.jwt_has_permissao(ARRAY['admin','superadmin']))
  WITH CHECK (public.jwt_has_permissao(ARRAY['admin','superadmin']));

DROP POLICY IF EXISTS logs_select_authenticated ON public.robot_logs;
CREATE POLICY logs_select_authenticated ON public.robot_logs
  FOR SELECT TO authenticated
  USING (public.jwt_has_permissao(ARRAY['admin','superadmin']));
