import Constants from "expo-constants";

// In dev, point to local backend. Override via app.json extra or env.
export const API_BASE_URL: string =
  Constants.expoConfig?.extra?.apiBaseUrl ?? "http://localhost:8000";

export const MOBILE_REDIRECT_URI = "precis://auth";
