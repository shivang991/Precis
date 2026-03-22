import { View, Text, Switch, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useApi } from "../../hooks/useApi";
import { useAuthStore } from "../../store/auth";

const THEMES = ["default", "dark", "sepia"] as const;

export default function GeneralSettingsScreen() {
  const router = useRouter();
  const api = useApi();
  const qc = useQueryClient();
  const logout = useAuthStore((s) => s.logout);

  const { data: user } = useQuery({
    queryKey: ["user"],
    queryFn: () => api.getProfile(),
  });

  const mutation = useMutation({
    mutationFn: (data: Parameters<typeof api.updateSettings>[0]) =>
      api.updateSettings(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["user"] }),
    onError: (e: any) => Alert.alert("Save failed", e.message),
  });

  return (
    <View style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Theme</Text>
        <View style={styles.themeRow}>
          {THEMES.map((t) => (
            <TouchableOpacity
              key={t}
              style={[styles.themeBtn, user?.theme === t && styles.themeBtnActive]}
              onPress={() => mutation.mutate({ theme: t })}
            >
              <Text
                style={[styles.themeBtnText, user?.theme === t && styles.themeBtnTextActive]}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.row}>
          <Text style={styles.label}>Include headings in summary</Text>
          <Switch
            value={user?.include_headings_in_summary ?? true}
            onValueChange={(v) => mutation.mutate({ include_headings_in_summary: v })}
          />
        </View>
      </View>

      <TouchableOpacity
        style={styles.logoutBtn}
        onPress={() => {
          logout();
          router.replace("/(auth)/login");
        }}
      >
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: "#fff" },
  section: { marginBottom: 32 },
  sectionTitle: { fontSize: 13, fontWeight: "600", color: "#888", marginBottom: 12, textTransform: "uppercase", letterSpacing: 0.5 },
  themeRow: { flexDirection: "row", gap: 8 },
  themeBtn: { paddingVertical: 8, paddingHorizontal: 16, borderRadius: 8, borderWidth: 1, borderColor: "#ccc" },
  themeBtnActive: { backgroundColor: "#1a1a1a", borderColor: "#1a1a1a" },
  themeBtnText: { fontSize: 14, color: "#333" },
  themeBtnTextActive: { color: "#fff" },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  label: { fontSize: 15, color: "#333" },
  logoutBtn: { marginTop: "auto", padding: 16, alignItems: "center" },
  logoutText: { fontSize: 15, color: "#e53935" },
});
