import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";

import { supabase } from "@/integrations/supabase/client";

export const Route = createFileRoute("/_authenticated")({
  // A sessão fica no browser; o servidor não consegue lê-la.
  ssr: false,
  beforeLoad: async ({ location }) => {
    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user) {
      throw redirect({ to: "/", search: { redirect: location.href } });
    }
    return { user: data.user };
  },
  component: () => <Outlet />,
});