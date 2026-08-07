/**
 * Guard do Linkai. A sessão vive em cookies httpOnly, então o servidor
 * consegue avaliá-la durante o SSR — sem flash de tela de login.
 */
import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";

import { getCurrentSession } from "@/lib/auth/session.functions";

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: async ({ location }) => {
    const { user } = await getCurrentSession();
    if (!user) {
      throw redirect({ to: "/", search: { next: location.href } });
    }
    return { user };
  },
  component: () => <Outlet />,
});