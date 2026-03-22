export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  theme: "default" | "dark" | "sepia";
  include_headings_in_summary: boolean;
  created_at: string;
}

export interface UserSettingsUpdate {
  theme?: "default" | "dark" | "sepia";
  include_headings_in_summary?: boolean;
}
