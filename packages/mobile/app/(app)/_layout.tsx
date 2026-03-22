import { Stack } from "expo-router";
import { useAuthStore } from "../../store/auth";
import { Redirect } from "expo-router";

export default function AppLayout() {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Redirect href="/(auth)/login" />;

  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: "Your Files" }} />
      <Stack.Screen name="settings" options={{ title: "General Settings" }} />
      <Stack.Screen
        name="documents/[id]"
        options={{ title: "Document", headerBackTitle: "Files" }}
      />
      <Stack.Screen
        name="documents/[id]/summary"
        options={{ title: "Summary", headerBackTitle: "Document" }}
      />
      <Stack.Screen
        name="documents/[id]/settings"
        options={{ title: "Document Settings", headerBackTitle: "Document" }}
      />
    </Stack>
  );
}
