import { useQuery } from "@tanstack/react-query";

import { getAppInfo, inApp } from "../lib/ipc";

export function useAppInfo() {
  return useQuery({
    queryKey: ["app-info"],
    queryFn: getAppInfo,
    enabled: inApp(),
    staleTime: Infinity,
    retry: false,
  });
}
