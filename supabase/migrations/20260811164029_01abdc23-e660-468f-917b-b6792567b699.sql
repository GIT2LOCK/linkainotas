DROP INDEX IF EXISTS public.usuarios_ariia_user_id_key;
CREATE UNIQUE INDEX usuarios_ariia_user_id_key ON public.usuarios USING btree (ariia_user_id);