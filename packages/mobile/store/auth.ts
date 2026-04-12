import { create } from "zustand";
import type { UserRead } from "@precis/shared";

interface AuthState {
  token: string | null;
  user: UserRead | null;
  setToken: (token: string) => void;
  setUser: (user: UserRead) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  setToken: (token) => set({ token }),
  setUser: (user) => set({ user }),
  logout: () => set({ token: null, user: null }),
}));
