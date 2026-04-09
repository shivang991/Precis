export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  created_at: string;
}

export type UserSettingsUpdate = Record<string, never>;
