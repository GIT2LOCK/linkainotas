REVOKE EXECUTE ON FUNCTION public.lumina_refresh_request(uuid) FROM anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.lumina_archive_job(uuid, text, text) FROM anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.enqueue_lumina_request(text, jsonb, jsonb) FROM anon;
GRANT EXECUTE ON FUNCTION public.enqueue_lumina_request(text, jsonb, jsonb) TO authenticated, service_role;