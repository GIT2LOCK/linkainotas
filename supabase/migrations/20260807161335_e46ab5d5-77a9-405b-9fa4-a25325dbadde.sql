-- pedidos_pendentes
DROP POLICY IF EXISTS pedidos_select_authenticated ON public.pedidos_pendentes;
DROP POLICY IF EXISTS pedidos_write_operador ON public.pedidos_pendentes;
REVOKE ALL ON public.pedidos_pendentes FROM authenticated;
REVOKE ALL ON public.pedidos_pendentes FROM anon;
GRANT ALL ON public.pedidos_pendentes TO service_role;
ALTER TABLE public.pedidos_pendentes ENABLE ROW LEVEL SECURITY;

-- notas_processadas
DROP POLICY IF EXISTS notas_select_authenticated ON public.notas_processadas;
DROP POLICY IF EXISTS notas_write_operador ON public.notas_processadas;
REVOKE ALL ON public.notas_processadas FROM authenticated;
REVOKE ALL ON public.notas_processadas FROM anon;
GRANT ALL ON public.notas_processadas TO service_role;
ALTER TABLE public.notas_processadas ENABLE ROW LEVEL SECURITY;

-- regras_imposto
DROP POLICY IF EXISTS regras_select_authenticated ON public.regras_imposto;
DROP POLICY IF EXISTS regras_write_admin ON public.regras_imposto;
REVOKE ALL ON public.regras_imposto FROM authenticated;
REVOKE ALL ON public.regras_imposto FROM anon;
GRANT ALL ON public.regras_imposto TO service_role;
ALTER TABLE public.regras_imposto ENABLE ROW LEVEL SECURITY;

-- robot_logs (mesmo motivo: sem escopo de empresa ainda)
DROP POLICY IF EXISTS logs_select_authenticated ON public.robot_logs;
REVOKE ALL ON public.robot_logs FROM authenticated;
REVOKE ALL ON public.robot_logs FROM anon;
GRANT ALL ON public.robot_logs TO service_role;
ALTER TABLE public.robot_logs ENABLE ROW LEVEL SECURITY;