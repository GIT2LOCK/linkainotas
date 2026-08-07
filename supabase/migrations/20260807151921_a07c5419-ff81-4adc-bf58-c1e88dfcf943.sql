CREATE TABLE public.ariia_identities (
  user_id UUID NOT NULL PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  ariia_user_id UUID NOT NULL UNIQUE,
  refresh_token_encrypted TEXT,
  expires_at TIMESTAMP WITH TIME ZONE,
  last_login_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

GRANT ALL ON public.ariia_identities TO service_role;

ALTER TABLE public.ariia_identities ENABLE ROW LEVEL SECURITY;

CREATE TRIGGER update_ariia_identities_updated_at
BEFORE UPDATE ON public.ariia_identities
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();