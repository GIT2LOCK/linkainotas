-- 1. Sequência de numeração das solicitações
CREATE SEQUENCE IF NOT EXISTS public.lumina_queue_number_seq AS bigint START 1 INCREMENT 1;

-- 2. Tabela de solicitações-pai
CREATE TABLE IF NOT EXISTS public.lumina_queue_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  queue_number bigint NOT NULL UNIQUE DEFAULT nextval('public.lumina_queue_number_seq'),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  requested_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  empresa_id integer REFERENCES public.empresas(id),
  action text NOT NULL DEFAULT 'launch_notes',
  status text NOT NULL DEFAULT 'queued',
  total_items integer NOT NULL DEFAULT 0,
  completed_items integer NOT NULL DEFAULT 0,
  failed_items integer NOT NULL DEFAULT 0,
  canceled_items integer NOT NULL DEFAULT 0,
  started_at timestamptz,
  finished_at timestamptz,
  message text,
  CONSTRAINT lumina_queue_requests_action_check CHECK (action IN ('launch_notes')),
  CONSTRAINT lumina_queue_requests_status_check CHECK (status IN ('queued','running','succeeded','failed','canceled')),
  CONSTRAINT lumina_queue_requests_totals_check CHECK (
    total_items >= 0
    AND completed_items >= 0 AND failed_items >= 0 AND canceled_items >= 0
    AND completed_items <= total_items
    AND failed_items <= total_items
    AND canceled_items <= total_items
    AND (completed_items + failed_items + canceled_items) <= total_items
  )
);

GRANT SELECT ON public.lumina_queue_requests TO authenticated;
GRANT ALL ON public.lumina_queue_requests TO service_role;
ALTER TABLE public.lumina_queue_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS lumina_queue_requests_select ON public.lumina_queue_requests;
CREATE POLICY lumina_queue_requests_select ON public.lumina_queue_requests
  FOR SELECT TO authenticated
  USING (
    public.jwt_has_permissao(ARRAY['superadmin'])
    OR requested_by = auth.uid()
    OR (public.jwt_has_permissao(ARRAY['admin']) AND empresa_id IS NOT NULL AND empresa_id = public.jwt_empresa_id())
  );

DROP POLICY IF EXISTS service_role_all_lumina_queue_requests ON public.lumina_queue_requests;
CREATE POLICY service_role_all_lumina_queue_requests ON public.lumina_queue_requests
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS lumina_queue_requests_updated_at ON public.lumina_queue_requests;
CREATE TRIGGER lumina_queue_requests_updated_at
  BEFORE UPDATE ON public.lumina_queue_requests
  FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();

CREATE INDEX IF NOT EXISTS idx_lumina_queue_requests_status_created
  ON public.lumina_queue_requests (status, created_at);
CREATE INDEX IF NOT EXISTS idx_lumina_queue_requests_requested_by_created
  ON public.lumina_queue_requests (requested_by, created_at DESC);

-- 3. Evolução da tabela de itens
ALTER TABLE public.lumina_jobs
  ADD COLUMN IF NOT EXISTS queue_request_id uuid,
  ADD COLUMN IF NOT EXISTS item_number integer NOT NULL DEFAULT 1;

-- 3.1 Agrupar itens ativos antigos em novas solicitações-pai
DO $migrate$
DECLARE
  v_user record;
  v_request_id uuid;
BEGIN
  FOR v_user IN
    SELECT requested_by, MIN(empresa_id) AS empresa_id, MIN(created_at) AS created_at, COUNT(*) AS total
    FROM public.lumina_jobs
    WHERE queue_request_id IS NULL AND status IN ('queued','running')
    GROUP BY requested_by
  LOOP
    INSERT INTO public.lumina_queue_requests (
      requested_by, empresa_id, action, status, total_items, created_at, message
    ) VALUES (
      v_user.requested_by, v_user.empresa_id, 'launch_notes', 'queued', v_user.total, v_user.created_at,
      'Solicitação criada automaticamente na migração da fila.'
    ) RETURNING id INTO v_request_id;

    WITH numerado AS (
      SELECT id, row_number() OVER (ORDER BY created_at, id) AS rn
      FROM public.lumina_jobs
      WHERE queue_request_id IS NULL AND status IN ('queued','running')
        AND requested_by = v_user.requested_by
    )
    UPDATE public.lumina_jobs j
       SET queue_request_id = v_request_id,
           item_number = n.rn
      FROM numerado n
     WHERE j.id = n.id;
  END LOOP;
END
$migrate$;

DO $fk$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'lumina_jobs_queue_request_id_fkey'
  ) THEN
    ALTER TABLE public.lumina_jobs
      ADD CONSTRAINT lumina_jobs_queue_request_id_fkey
      FOREIGN KEY (queue_request_id) REFERENCES public.lumina_queue_requests(id) ON DELETE CASCADE;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'lumina_jobs_request_item_unique'
  ) THEN
    ALTER TABLE public.lumina_jobs
      ADD CONSTRAINT lumina_jobs_request_item_unique UNIQUE (queue_request_id, item_number);
  END IF;
END
$fk$;

CREATE INDEX IF NOT EXISTS idx_lumina_jobs_status_created ON public.lumina_jobs (status, created_at);
CREATE INDEX IF NOT EXISTS idx_lumina_jobs_leased_until ON public.lumina_jobs (leased_until) WHERE status = 'running';
CREATE INDEX IF NOT EXISTS idx_lumina_jobs_requested_by_created ON public.lumina_jobs (requested_by, created_at);

-- 3.2 Nenhuma escrita direta na fila pelo usuário
DROP POLICY IF EXISTS lumina_jobs_insert ON public.lumina_jobs;
DROP POLICY IF EXISTS service_role_all_lumina_jobs ON public.lumina_jobs;
CREATE POLICY service_role_all_lumina_jobs ON public.lumina_jobs
  FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE INSERT, UPDATE, DELETE ON public.lumina_jobs FROM authenticated;
GRANT SELECT ON public.lumina_jobs TO authenticated;
GRANT ALL ON public.lumina_jobs TO service_role;

-- 4. Histórico permanente
CREATE TABLE IF NOT EXISTS public.lumina_queue_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  queue_request_id uuid REFERENCES public.lumina_queue_requests(id) ON DELETE SET NULL,
  queue_item_id uuid NOT NULL,
  queue_number bigint NOT NULL,
  item_number integer NOT NULL,
  requested_by uuid,
  empresa_id integer,
  action text,
  status text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  worker_id text,
  attempts integer NOT NULL DEFAULT 0,
  queued_at timestamptz,
  started_at timestamptz,
  finished_at timestamptz NOT NULL DEFAULT now(),
  message text,
  CONSTRAINT lumina_queue_logs_status_check CHECK (status IN ('succeeded','failed','canceled'))
);

GRANT SELECT ON public.lumina_queue_logs TO authenticated;
GRANT ALL ON public.lumina_queue_logs TO service_role;
ALTER TABLE public.lumina_queue_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS lumina_queue_logs_select ON public.lumina_queue_logs;
CREATE POLICY lumina_queue_logs_select ON public.lumina_queue_logs
  FOR SELECT TO authenticated
  USING (
    public.jwt_has_permissao(ARRAY['superadmin'])
    OR requested_by = auth.uid()
    OR (public.jwt_has_permissao(ARRAY['admin']) AND empresa_id IS NOT NULL AND empresa_id = public.jwt_empresa_id())
  );

DROP POLICY IF EXISTS service_role_all_lumina_queue_logs ON public.lumina_queue_logs;
CREATE POLICY service_role_all_lumina_queue_logs ON public.lumina_queue_logs
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_lumina_queue_logs_request_finished
  ON public.lumina_queue_logs (queue_request_id, finished_at DESC);

-- 5. Entrada na fila
CREATE OR REPLACE FUNCTION public.enqueue_lumina_request(
  p_action text DEFAULT 'launch_notes',
  p_payload jsonb DEFAULT '{}'::jsonb,
  p_items jsonb DEFAULT '[]'::jsonb
)
RETURNS public.lumina_queue_requests
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  v_user uuid := auth.uid();
  v_empresa integer := public.jwt_empresa_id();
  v_items jsonb := COALESCE(p_items, '[]'::jsonb);
  v_count integer;
  v_request public.lumina_queue_requests;
BEGIN
  IF v_user IS NULL OR NOT public.jwt_ativo() THEN
    RAISE EXCEPTION 'Usuário não autenticado ou inativo.' USING ERRCODE = '42501';
  END IF;

  IF COALESCE(p_action, 'launch_notes') <> 'launch_notes' THEN
    RAISE EXCEPTION 'Ação inválida para a fila do Lumina: %', p_action;
  END IF;

  IF jsonb_typeof(v_items) <> 'array' THEN
    RAISE EXCEPTION 'A lista de itens deve ser um array JSON.';
  END IF;

  IF jsonb_array_length(v_items) = 0 THEN
    v_items := jsonb_build_array(COALESCE(p_payload, '{}'::jsonb));
  END IF;

  v_count := jsonb_array_length(v_items);
  IF v_count > 1000 THEN
    RAISE EXCEPTION 'A solicitação excede o limite de 1000 itens.';
  END IF;

  INSERT INTO public.lumina_queue_requests (
    requested_by, empresa_id, action, status, total_items, message
  ) VALUES (
    v_user, v_empresa, 'launch_notes', 'queued', v_count,
    'Solicitação registrada na fila. Aguardando uma máquina disponível.'
  ) RETURNING * INTO v_request;

  INSERT INTO public.lumina_jobs (
    requested_by, empresa_id, action, status, payload, message, queue_request_id, item_number
  )
  SELECT
    v_user, v_empresa, 'launch_notes', 'queued',
    CASE WHEN jsonb_typeof(item.value) = 'object' THEN item.value ELSE jsonb_build_object('value', item.value) END,
    'Solicitação registrada na fila. Aguardando uma máquina disponível.',
    v_request.id, item.ordinality::int
  FROM jsonb_array_elements(v_items) WITH ORDINALITY AS item(value, ordinality);

  RETURN v_request;
END;
$$;

REVOKE ALL ON FUNCTION public.enqueue_lumina_request(text, jsonb, jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.enqueue_lumina_request(text, jsonb, jsonb) TO authenticated, service_role;

-- 6. Recalcular a solicitação-pai
CREATE OR REPLACE FUNCTION public.lumina_refresh_request(p_request_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  v_ok integer; v_failed integer; v_canceled integer;
  v_pending integer; v_running integer; v_status text;
BEGIN
  IF p_request_id IS NULL THEN RETURN; END IF;

  PERFORM 1 FROM public.lumina_queue_requests WHERE id = p_request_id FOR UPDATE;

  SELECT
    COUNT(*) FILTER (WHERE status = 'succeeded'),
    COUNT(*) FILTER (WHERE status = 'failed'),
    COUNT(*) FILTER (WHERE status = 'canceled')
    INTO v_ok, v_failed, v_canceled
  FROM public.lumina_queue_logs WHERE queue_request_id = p_request_id;

  SELECT COUNT(*), COUNT(*) FILTER (WHERE status = 'running')
    INTO v_pending, v_running
  FROM public.lumina_jobs WHERE queue_request_id = p_request_id;

  IF v_pending > 0 THEN
    v_status := CASE WHEN v_running > 0 THEN 'running' ELSE 'queued' END;
  ELSIF v_canceled > 0 THEN
    v_status := 'canceled';
  ELSIF v_failed > 0 THEN
    v_status := 'failed';
  ELSE
    v_status := 'succeeded';
  END IF;

  UPDATE public.lumina_queue_requests
     SET completed_items = v_ok,
         failed_items = v_failed,
         canceled_items = v_canceled,
         status = v_status,
         started_at = CASE WHEN v_status = 'queued' THEN started_at ELSE COALESCE(started_at, now()) END,
         finished_at = CASE WHEN v_pending = 0 THEN COALESCE(finished_at, now()) ELSE NULL END
   WHERE id = p_request_id;
END;
$$;

REVOKE ALL ON FUNCTION public.lumina_refresh_request(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.lumina_refresh_request(uuid) TO service_role;

-- 7. Arquivar item: log + contadores + remoção (atômico)
CREATE OR REPLACE FUNCTION public.lumina_archive_job(p_job_id uuid, p_status text, p_message text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  v_job public.lumina_jobs;
  v_number bigint;
  v_request uuid;
BEGIN
  SELECT * INTO v_job FROM public.lumina_jobs WHERE id = p_job_id FOR UPDATE;
  IF NOT FOUND THEN RETURN false; END IF;

  SELECT queue_number INTO v_number
  FROM public.lumina_queue_requests WHERE id = v_job.queue_request_id;

  INSERT INTO public.lumina_queue_logs (
    queue_request_id, queue_item_id, queue_number, item_number, requested_by, empresa_id,
    action, status, payload, worker_id, attempts, queued_at, started_at, finished_at, message
  ) VALUES (
    v_job.queue_request_id, v_job.id, COALESCE(v_number, 0), COALESCE(v_job.item_number, 1),
    v_job.requested_by, v_job.empresa_id, v_job.action, p_status, COALESCE(v_job.payload, '{}'::jsonb),
    v_job.worker_id, v_job.attempts, v_job.created_at, v_job.started_at, now(), p_message
  );

  v_request := v_job.queue_request_id;
  DELETE FROM public.lumina_jobs WHERE id = v_job.id;
  PERFORM public.lumina_refresh_request(v_request);
  RETURN true;
END;
$$;

REVOKE ALL ON FUNCTION public.lumina_archive_job(uuid, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.lumina_archive_job(uuid, text, text) TO service_role;

-- 8. Reserva atômica (assinatura preservada)
CREATE OR REPLACE FUNCTION public.claim_lumina_job(p_worker_id text, p_lease_seconds integer DEFAULT 300)
RETURNS SETOF public.lumina_jobs
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  claimed public.lumina_jobs;
  exhausted public.lumina_jobs;
BEGIN
  -- Itens que esgotaram as tentativas viram falha definitiva
  FOR exhausted IN
    SELECT * FROM public.lumina_jobs
     WHERE attempts >= 3
       AND (status = 'queued' OR (status = 'running' AND leased_until < now()))
     FOR UPDATE SKIP LOCKED
  LOOP
    PERFORM public.lumina_archive_job(
      exhausted.id, 'failed',
      'Limite de tentativas atingido sem conclusão do atendimento Lumina.'
    );
  END LOOP;

  SELECT j.* INTO claimed
    FROM public.lumina_jobs j
   WHERE (j.status = 'queued' OR (j.status = 'running' AND j.leased_until < now()))
     AND j.attempts < 3
     AND NOT EXISTS (
       SELECT 1 FROM public.lumina_jobs o
        WHERE o.requested_by = j.requested_by
          AND o.id <> j.id
          AND o.status = 'running'
          AND o.leased_until >= now()
     )
   ORDER BY j.created_at, j.item_number
     FOR UPDATE SKIP LOCKED
   LIMIT 1;

  IF NOT FOUND THEN RETURN; END IF;

  -- Serializa por usuário entre máquinas concorrentes
  PERFORM pg_advisory_xact_lock(hashtextextended(claimed.requested_by::text, 0));

  IF EXISTS (
    SELECT 1 FROM public.lumina_jobs o
     WHERE o.requested_by = claimed.requested_by
       AND o.id <> claimed.id
       AND o.status = 'running'
       AND o.leased_until >= now()
  ) THEN
    RETURN;
  END IF;

  UPDATE public.lumina_jobs
     SET status = 'running',
         worker_id = p_worker_id,
         attempts = attempts + 1,
         leased_until = now() + make_interval(secs => GREATEST(60, COALESCE(p_lease_seconds, 300))),
         heartbeat_at = now(),
         started_at = COALESCE(started_at, now()),
         message = 'Solicitação reservada por uma máquina disponível.'
   WHERE id = claimed.id
   RETURNING * INTO claimed;

  UPDATE public.lumina_queue_requests
     SET status = 'running',
         started_at = COALESCE(started_at, now()),
         finished_at = NULL,
         message = 'Uma máquina disponível iniciou o atendimento.'
   WHERE id = claimed.queue_request_id
     AND status IN ('queued', 'running');

  RETURN NEXT claimed;
END;
$$;

-- 9. Renovação (assinatura preservada)
CREATE OR REPLACE FUNCTION public.renew_lumina_job(p_job_id uuid, p_worker_id text, p_lease_seconds integer DEFAULT 300)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
  UPDATE public.lumina_jobs
     SET leased_until = now() + make_interval(secs => GREATEST(60, COALESCE(p_lease_seconds, 300))),
         heartbeat_at = now()
   WHERE id = p_job_id
     AND worker_id = p_worker_id
     AND status = 'running'
  RETURNING true;
$$;

-- 10. Devolução à fila (assinatura preservada)
CREATE OR REPLACE FUNCTION public.release_lumina_job(p_job_id uuid, p_worker_id text, p_message text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  v_request uuid;
BEGIN
  UPDATE public.lumina_jobs
     SET status = 'queued',
         worker_id = NULL,
         leased_until = NULL,
         heartbeat_at = NULL,
         message = COALESCE(NULLIF(p_message, ''), 'A máquina ficou ocupada; a solicitação voltou para a fila.')
   WHERE id = p_job_id
     AND worker_id = p_worker_id
     AND status = 'running'
  RETURNING queue_request_id INTO v_request;

  IF NOT FOUND THEN RETURN false; END IF;

  PERFORM public.lumina_refresh_request(v_request);
  RETURN true;
END;
$$;

-- 11. Finalização atômica (assinatura preservada)
CREATE OR REPLACE FUNCTION public.finish_lumina_job(p_job_id uuid, p_worker_id text, p_status text, p_message text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  v_exists boolean;
BEGIN
  IF p_status NOT IN ('succeeded', 'failed', 'canceled') THEN
    RAISE EXCEPTION 'Invalid Lumina job status: %', p_status;
  END IF;

  SELECT true INTO v_exists
    FROM public.lumina_jobs
   WHERE id = p_job_id AND worker_id = p_worker_id AND status = 'running'
     FOR UPDATE;

  IF NOT FOUND THEN RETURN false; END IF;

  RETURN public.lumina_archive_job(p_job_id, p_status, p_message);
END;
$$;

-- 12. RPCs operacionais restritos ao service_role
REVOKE ALL ON FUNCTION public.claim_lumina_job(text, integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.renew_lumina_job(uuid, text, integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.release_lumina_job(uuid, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.finish_lumina_job(uuid, text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.claim_lumina_job(text, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.renew_lumina_job(uuid, text, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_lumina_job(uuid, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.finish_lumina_job(uuid, text, text, text) TO service_role;