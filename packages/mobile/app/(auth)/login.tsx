import { useEffect } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from "react-native";
import * as WebBrowser from "expo-web-browser";
import { useAuthRequest, makeRedirectUri } from "expo-auth-session";
import { useRouter } from "expo-router";
import { useAuthStore } from "../../store/auth";
import { createApiClient } from "@precis/shared";
import { API_BASE_URL, MOBILE_REDIRECT_URI } from "../../constants/api";

WebBrowser.maybeCompleteAuthSession();

const api = createApiClient(API_BASE_URL, () => null);

export default function LoginScreen() {
  const router = useRouter();
  const { setToken, setUser } = useAuthStore();

  const redirectUri = makeRedirectUri({ scheme: "precis", path: "auth" });

  const [request, response, promptAsync] = useAuthRequest(
    {
      clientId: "", // Not needed — we redirect through our backend
      redirectUri,
      scopes: [],
      // We open our backend's /api/v1/auth/login URL directly instead
    },
    { authorizationEndpoint: `${API_BASE_URL}/api/v1/auth/login` }
  );

  useEffect(() => {
    if (response?.type === "success") {
      const { code } = response.params;
      handleCodeExchange(code);
    } else if (response?.type === "error") {
      Alert.alert("Login failed", response.error?.message ?? "Unknown error");
    }
  }, [response]);

  async function handleCodeExchange(code: string) {
    try {
      const { access_token } = await api.exchangeCode(code, redirectUri);
      setToken(access_token);
      const user = await createApiClient(API_BASE_URL, () => access_token).getMe();
      setUser(user);
      router.replace("/(app)");
    } catch (e: any) {
      Alert.alert("Login failed", e.message ?? "Could not exchange code");
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Precis</Text>
      <Text style={styles.subtitle}>Your intelligent document companion</Text>
      <TouchableOpacity
        style={styles.button}
        onPress={() => promptAsync()}
        disabled={!request}
      >
        {!request ? (
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
