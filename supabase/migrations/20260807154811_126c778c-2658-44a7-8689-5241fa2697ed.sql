-- search_path fixo + SECURITY INVOKER (a RLS de usuarios já permite ler o próprio registro)
CREATE OR REPLACE FUNCTION public.get_usuario_atual()
RETURNS TABLE(id integer, nome character varying, email character varying, permissao character varying, empresa_id integer)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  SELECT u.id, u.nome, u.email, u.permissao, u.empresa_id
  FROM public.usuarios u
  WHERE u.auth_user_id = auth.uid();
$$;

REVOKE EXECUTE ON FUNCTION public.get_usuario_atual() FROM PUBLIC, anon;
GRANT  EXECUTE ON FUNCTION public.get_usuario_atual() TO authenticated, service_role;

CREATE OR REPLACE FUNCTION public.buscar_pedido_nf(p_cnpj character varying, p_valor numeric)
RETURNS TABLE(pedido_id uuid, numero_pedido character varying, numero_medicao character varying)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  SELECT id, numero_pedido, numero_medicao
  FROM public.pedidos_pendentes
  WHERE cnpj_fornecedor = p_cnpj
    AND valor_medicao_liquido = p_valor
    AND status = 'PENDENTE';
$$;

REVOKE EXECUTE ON FUNCTION public.buscar_pedido_nf(character varying, numeric) FROM PUBLIC, anon;
GRANT  EXECUTE ON FUNCTION public.buscar_pedido_nf(character varying, numeric) TO authenticated, service_role;

CREATE OR REPLACE FUNCTION public.vincular_nf_pedido(p_nf_id uuid, p_pedido_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
  UPDATE public.notas_processadas
     SET pedido_vinculado = p_pedido_id,
         status_matching  = 'MATCH_OK'
   WHERE id = p_nf_id;

  UPDATE public.pedidos_pendentes
     SET status = 'VINCULADO'
   WHERE id = p_pedido_id;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.vincular_nf_pedido(uuid, uuid) FROM PUBLIC, anon;
GRANT  EXECUTE ON FUNCTION public.vincular_nf_pedido(uuid, uuid) TO authenticated, service_role;

CREATE OR REPLACE FUNCTION public.update_timestamp()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- Função de event trigger: só o dono do banco deve poder executar.
REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;
