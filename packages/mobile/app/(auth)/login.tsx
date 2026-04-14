import { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from "react-native";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import { makeRedirectUri } from "expo-auth-session";
import { useRouter } from "expo-router";
import { useAuthStore } from "../../store/auth";
import { createApiClient } from "@precis/shared";
import { API_BASE_URL } from "../../constants/api";

WebBrowser.maybeCompleteAuthSession();

const api = createApiClient(API_BASE_URL, () => null);

export default function LoginScreen() {
  const router = useRouter();
  const { setToken, setUser } = useAuthStore();
  const [loading, setLoading] = useState(false);

  const redirectUri = makeRedirectUri({ scheme: "precis", path: "auth" });

  async function handleLogin() {
    setLoading(true);
    try {
      // 1. Ask the backend for the Google OAuth URL, passing our deep-link
      //    redirect URI so the callback knows where to send the token.
      const { url } = await api.getLoginUrl({ redirect_uri: redirectUri });

      // 2. Open the Google consent screen.  The backend callback will
      //    redirect to  precis://auth?access_token=<jwt>  after exchange.
      const result = await WebBrowser.openAuthSessionAsync(url, redirectUri);

      if (result.type === "success") {
        const parsed = Linking.parse(result.url);
        const accessToken = parsed.queryParams?.access_token as
          | string
          | undefined;
        if (!accessToken) throw new Error("No access token in redirect");

        setToken(accessToken);
        const user = await createApiClient(
          API_BASE_URL,
          () => accessToken,
        ).getAuthMe();
        setUser(user);
        router.replace("/(app)");
      }
    } catch (e: any) {
      Alert.alert("Login failed", e.message ?? "Could not complete login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Precis</Text>
      <Text style={styles.subtitle}>Your intelligent document companion</Text>
      <TouchableOpacity
        style={styles.button}
        onPress={handleLogin}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Continue with Google</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 32,
    backgroundColor: "#fff",
  },
  title: {
    fontSize: 40,
    fontWeight: "700",
    marginBottom: 8,
    letterSpacing: -1,
  },
  subtitle: {
    fontSize: 16,
    color: "#666",
    marginBottom: 48,
    textAlign: "center",
  },
  button: {
    backgroundColor: "#1a1a1a",
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 12,
    minWidth: 240,
    alignItems: "center",
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});
