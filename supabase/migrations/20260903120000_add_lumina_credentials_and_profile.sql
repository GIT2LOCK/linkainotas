-- ================================================================
-- LinkAI: credenciais iniciais do Lumina e perfil do usuário
--
-- A senha nunca fica em texto puro. O servidor do LinkAI cifra o valor
-- antes de gravar lumina_password_ciphertext. Os workers Windows usam a
-- mesma chave de cifragem para descriptografar somente durante o login.
-- ================================================================

ALTER TABLE public.usuarios
  ADD COLUMN IF NOT EXISTS lumina_username text,
  ADD COLUMN IF NOT EXISTS lumina_password_ciphertext text,
  ADD COLUMN IF NOT EXISTS lumina_password_set boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS lumina_credentials_updated_at timestamptz,
  ADD COLUMN IF NOT EXISTS avatar_customized boolean NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS usuarios_lumina_credentials_idx
  ON public.usuarios (lumina_password_set) WHERE lumina_password_set;

-- O perfil pode consultar apenas o indicador da senha, nunca o texto cifrado.
REVOKE SELECT ON public.usuarios FROM authenticated;
GRANT SELECT (
  id, auth_user_id, ariia_user_id, nome, email, permissao, empresa_id,
  avatar_url, avatar_customized, ativo, is_platform_superadmin,
  two_factor_policy, lumina_username, lumina_password_set,
  lumina_credentials_updated_at
) ON public.usuarios TO authenticated;
GRANT ALL ON public.usuarios TO service_role;

-- Bucket público somente para exibição das fotos de perfil. A escrita fica
-- limitada à pasta do próprio auth.uid().
INSERT INTO storage.buckets (id, name, public)
VALUES ('linkai-avatars', 'linkai-avatars', true)
ON CONFLICT (id) DO UPDATE SET public = true;

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
