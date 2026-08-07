import { queryOptions, useQuery } from "@tanstack/react-query";

import { getMyProfile } from "./auth.functions";

export const profileQueryOptions = queryOptions({
  queryKey: ["auth", "profile"],
  queryFn: () => getMyProfile(),
  staleTime: 60_000,
});

export function useProfile() {
  return useQuery(profileQueryOptions);
}