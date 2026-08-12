import { createFileRoute } from "@tanstack/react-router";

import { LuminaApp } from "@/features/lumina/LuminaApp";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [
      { title: "LinkAI Lumina | Linka Engenharia" },
      {
        name: "description",
        content: "Automação Lumina e processamento fiscal do LinkAI.",
      },
      { property: "og:title", content: "LinkAI Lumina" },
      {
        property: "og:description",
        content: "Automação Lumina e processamento fiscal do LinkAI.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const { user } = Route.useRouteContext();

  return <LuminaApp user={user} />;
}
