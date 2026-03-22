import { useMemo } from "react";
import { createApiClient } from "@precis/shared";
import { useAuthStore } from "../store/auth";
import { API_BASE_URL } from "../constants/api";

export function useApi() {
  const token = useAuthStore((s) => s.token);
  return useMemo(
    () => createApiClient(API_BASE_URL, () => token),
    [token]
  );
}
