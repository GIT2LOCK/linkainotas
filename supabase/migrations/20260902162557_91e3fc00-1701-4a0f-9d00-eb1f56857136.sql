-- anon não executa nada do modelo interno
REVOKE ALL ON FUNCTION public.linkai_assign_user_to_obra(integer, uuid, text, boolean) FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_create_obra(integer, text, text, text) FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_link_convite(text) FROM anon, authenticated, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_log_activity(text, text, jsonb, text, uuid, timestamptz, timestamptz) FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_ensure_escritorio(integer) FROM anon, authenticated, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_empresa_escritorio_trigger() FROM anon, authenticated, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_current_usuario() FROM anon, authenticated, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_obra_principal(integer) FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_perfil_principal(integer) FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_current_usuario_id() FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_current_empresa_id() FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_is_platform_superadmin() FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_is_supervisor() FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_has_permissao(text) FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_obras_visiveis() FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_can_access_obra(uuid) FROM anon, PUBLIC;
REVOKE ALL ON FUNCTION public.linkai_can_manage_empresa(integer) FROM anon, PUBLIC;

-- service_role executa tudo o que o robô precisa
GRANT EXECUTE ON FUNCTION public.linkai_link_convite(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.linkai_ensure_escritorio(integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.linkai_current_usuario() TO service_role;
GRANT EXECUTE ON FUNCTION public.linkai_obra_principal(integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.linkai_perfil_principal(integer) TO service_role;

-- authenticated: apenas RPCs de uso do app + helpers usados nas policies
GRANT EXECUTE ON FUNCTION public.linkai_assign_user_to_obra(integer, uuid, text, boolean) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.linkai_create_obra(integer, text, text, text) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.linkai_log_activity(text, text, jsonb, text, uuid, timestamptz, timestamptz) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.linkai_obra_principal(integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.linkai_perfil_principal(integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.linkai_current_usuario_id() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.linkai_current_empresa_id() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.linkai_is_platform_superadmin() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.linkai_is_supervisor() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.linkai_has_permissao(text) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.linkai_obras_visiveis() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.linkai_can_access_obra(uuid) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.linkai_can_manage_empresa(integer) TO authenticated, service_role;