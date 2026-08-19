-- Queue durable requests for Lumina desktop workers.

CREATE TABLE IF NOT EXISTS public.lumina_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  requested_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  empresa_id integer REFERENCES public.empresas(id) ON DELETE SET NULL,
  action text NOT NULL DEFAULT 'launch_notes'
    CHECK (action = 'launch_notes'),
  status text NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'canceled')),
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  worker_id text,
  attempts integer NOT NULL DEFAULT 0,
  leased_until timestamptz,
  heartbeat_at timestamptz,
  started_at timestamptz,
  finished_at timestamptz,
  message text
);

CREATE INDEX IF NOT EXISTS lumina_jobs_queue_idx
  ON public.lumina_jobs (status, created_at)
  WHERE status = 'queued';

CREATE INDEX IF NOT EXISTS lumina_jobs_active_idx
  ON public.lumina_jobs (leased_until)
  WHERE status = 'running';

DROP TRIGGER IF EXISTS lumina_jobs_updated_at ON public.lumina_jobs;
CREATE TRIGGER lumina_jobs_updated_at
  BEFORE UPDATE ON public.lumina_jobs
  FOR EACH ROW
  EXECUTE FUNCTION public.update_timestamp();

ALTER TABLE public.lumina_jobs ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT ON public.lumina_jobs TO authenticated;
GRANT ALL ON public.lumina_jobs TO service_role;

DROP POLICY IF EXISTS lumina_jobs_select ON public.lumina_jobs;
CREATE POLICY lumina_jobs_select ON public.lumina_jobs
  FOR SELECT TO authenticated
  USING (
    public.jwt_has_permissao(ARRAY['superadmin'])
    OR requested_by = auth.uid()
    OR (
      public.jwt_has_permissao(ARRAY['admin'])
      AND empresa_id IS NOT NULL
      AND empresa_id = public.jwt_empresa_id()
    )
  );

DROP POLICY IF EXISTS lumina_jobs_insert ON public.lumina_jobs;
CREATE POLICY lumina_jobs_insert ON public.lumina_jobs
  FOR INSERT TO authenticated
  WITH CHECK (
    requested_by = auth.uid()
    AND public.jwt_ativo()
    AND (
      public.jwt_has_permissao(ARRAY['superadmin'])
      OR empresa_id = public.jwt_empresa_id()
    )
  );

CREATE OR REPLACE FUNCTION public.claim_lumina_job(
  p_worker_id text,
  p_lease_seconds integer DEFAULT 300
)
RETURNS SETOF public.lumina_jobs
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  claimed public.lumina_jobs;
BEGIN
  SELECT *
    INTO claimed
    FROM public.lumina_jobs
   WHERE (
     status = 'queued'
     OR (status = 'running' AND leased_until < now())
   )
     AND attempts < 3
   ORDER BY created_at
   FOR UPDATE SKIP LOCKED
   LIMIT 1;

  IF NOT FOUND THEN
    RETURN;
  END IF;

  UPDATE public.lumina_jobs
     SET status = 'running',
         worker_id = p_worker_id,
         attempts = attempts + 1,
         leased_until = now() + make_interval(secs => GREATEST(60, p_lease_seconds)),
         heartbeat_at = now(),
         started_at = COALESCE(started_at, now()),
         message = 'Solicitação reservada por uma máquina disponível.'
   WHERE id = claimed.id
   RETURNING * INTO claimed;

  RETURN NEXT claimed;
END;
$$;

CREATE OR REPLACE FUNCTION public.renew_lumina_job(
  p_job_id uuid,
  p_worker_id text,
  p_lease_seconds integer DEFAULT 300
)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  UPDATE public.lumina_jobs
     SET leased_until = now() + make_interval(secs => GREATEST(60, p_lease_seconds)),
         heartbeat_at = now()
   WHERE id = p_job_id
     AND worker_id = p_worker_id
     AND status = 'running'
  RETURNING true;
$$;

CREATE OR REPLACE FUNCTION public.release_lumina_job(
  p_job_id uuid,
  p_worker_id text,
  p_message text
)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  UPDATE public.lumina_jobs
     SET status = 'queued',
         worker_id = NULL,
         leased_until = NULL,
         heartbeat_at = NULL,
         message = COALESCE(NULLIF(p_message, ''), 'A máquina ficou ocupada; a solicitação voltou para a fila.')
   WHERE id = p_job_id
     AND worker_id = p_worker_id
     AND status = 'running'
  RETURNING true;
$$;

CREATE OR REPLACE FUNCTION public.finish_lumina_job(
  p_job_id uuid,
  p_worker_id text,
  p_status text,
  p_message text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF p_status NOT IN ('succeeded', 'failed', 'canceled') THEN
    RAISE EXCEPTION 'Invalid Lumina job status: %', p_status;
  END IF;

  UPDATE public.lumina_jobs
     SET status = p_status,
         leased_until = NULL,
         heartbeat_at = now(),
         finished_at = now(),
         message = p_message
   WHERE id = p_job_id
     AND worker_id = p_worker_id
     AND status = 'running';

  RETURN FOUND;
END;
$$;

REVOKE ALL ON FUNCTION public.claim_lumina_job(text, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.renew_lumina_job(uuid, text, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_lumina_job(uuid, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.finish_lumina_job(uuid, text, text, text) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.claim_lumina_job(text, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.renew_lumina_job(uuid, text, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_lumina_job(uuid, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.finish_lumina_job(uuid, text, text, text) TO service_role;

