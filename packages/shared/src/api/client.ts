import axios from "axios";
import type { AxiosResponse } from "axios";
import { getAuth } from "../generated/auth/auth";
import { getDocuments } from "../generated/documents/documents";
import { getHighlights } from "../generated/highlights/highlights";
import { getUsers } from "../generated/users/users";

type UnwrapAxiosResponse<T> = {
  [K in keyof T]: T[K] extends (...args: infer A) => Promise<AxiosResponse<infer R>>
    ? (...args: A) => Promise<R>
    : T[K];
};

export function createApiClient(
  baseURL: string,
  getToken: () => string | null,
) {
  const instance = axios.create({ baseURL });

  instance.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // Auto-unwrap response data so callers get `Promise<T>` instead of `Promise<AxiosResponse<T>>`
  instance.interceptors.response.use((response) => response.data as any);

  const raw = {
    ...getAuth(instance),
    ...getDocuments(instance),
    ...getHighlights(instance),
    ...getUsers(instance),
  };

  return raw as unknown as UnwrapAxiosResponse<typeof raw>;
}

export type ApiClient = ReturnType<typeof createApiClient>;
