ALTER TABLE public.usuarios
  ADD COLUMN IF NOT EXISTS lumina_username text,
  ADD COLUMN IF NOT EXISTS lumina_password_ciphertext text,
  ADD COLUMN IF NOT EXISTS lumina_password_set boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS lumina_credentials_updated_at timestamptz,
  ADD COLUMN IF NOT EXISTS avatar_customized boolean NOT NULL DEFAULT false;

REVOKE SELECT ON public.usuarios FROM authenticated;
GRANT SELECT (
  id, auth_user_id, ariia_user_id, nome, email, permissao, empresa_id,
  avatar_url, avatar_customized, ativo, is_platform_superadmin,
  two_factor_policy, criado_em, atualizado_em, lumina_username,
  lumina_password_set, lumina_credentials_updated_at
) ON public.usuarios TO authenticated;
GRANT ALL ON public.usuarios TO service_role;

DROP POLICY IF EXISTS linkai_avatars_select_own ON storage.objects;
CREATE POLICY linkai_avatars_select_own
  ON storage.objects FOR SELECT TO authenticated
  USING (
    bucket_id = 'linkai-avatars'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

DROP POLICY IF EXISTS linkai_avatars_insert_own ON storage.objects;
CREATE POLICY linkai_avatars_insert_own
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'linkai-avatars'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

DROP POLICY IF EXISTS linkai_avatars_update_own ON storage.objects;
CREATE POLICY linkai_avatars_update_own
  ON storage.objects FOR UPDATE TO authenticated
  USING (
    bucket_id = 'linkai-avatars'
    AND (storage.foldername(name))[1] = auth.uid()::text
  )
  WITH CHECK (
    bucket_id = 'linkai-avatars'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

DROP POLICY IF EXISTS linkai_avatars_delete_own ON storage.objects;
CREATE POLICY linkai_avatars_delete_own
  ON storage.objects FOR DELETE TO authenticated
  USING (
    bucket_id = 'linkai-avatars'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );