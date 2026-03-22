import React from "react";
import {
  View,
  Text,
  TextInput,
  Switch,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useApi } from "../../../../hooks/useApi";

const THEMES = ["default", "dark", "sepia"] as const;

export default function DocumentSettingsScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const api = useApi();
  const qc = useQueryClient();

  const { data: document } = useQuery({
    queryKey: ["document", id],
    queryFn: () => api.getDocument(id),
    enabled: !!id,
  });

  const [title, setTitle] = React.useState("");
  React.useEffect(() => {
    if (document?.title) setTitle(document.title);
  }, [document?.title]);

  const mutation = useMutation({
    mutationFn: (data: Parameters<typeof api.updateDocumentSettings>[1]) =>
      api.updateDocumentSettings(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["document", id] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (e: any) => Alert.alert("Save failed", e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteDocument(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      router.replace("/(app)");
    },
    onError: (e: any) => Alert.alert("Delete failed", e.message),
  });

  const confirmDelete = () => {
    Alert.alert("Delete Document", "This cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      { text: "Delete", style: "destructive", onPress: () => deleteMutation.mutate() },
    ]);
  };

  if (!document) return <ActivityIndicator style={{ marginTop: 48 }} />;

  return (
    <View style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Title</Text>
        <TextInput
          style={styles.input}
          value={title}
          onChangeText={setTitle}
          onBlur={() => title !== document.title && mutation.mutate({ title })}
          returnKeyType="done"
          onSubmitEditing={() => title !== document.title && mutation.mutate({ title })}
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Theme</Text>
        <View style={styles.themeRow}>
          {THEMES.map((t) => (
            <TouchableOpacity
              key={t}
              style={[styles.themeBtn, document.theme === t && styles.themeBtnActive]}
              onPress={() => mutation.mutate({ theme: t })}
            >
              <Text style={[styles.themeBtnText, document.theme === t && styles.themeBtnTextActive]}>
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
            value={document.include_headings_in_summary ?? true}
            onValueChange={(v) => mutation.mutate({ include_headings_in_summary: v })}
          />
        </View>
      </View>

      <TouchableOpacity style={styles.deleteBtn} onPress={confirmDelete}>
        <Text style={styles.deleteText}>Delete Document</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: "#fff" },
  section: { marginBottom: 28 },
  sectionTitle: { fontSize: 13, fontWeight: "600", color: "#888", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 },
  input: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 10, fontSize: 15 },
  themeRow: { flexDirection: "row", gap: 8 },
  themeBtn: { paddingVertical: 8, paddingHorizontal: 16, borderRadius: 8, borderWidth: 1, borderColor: "#ccc" },
  themeBtnActive: { backgroundColor: "#1a1a1a", borderColor: "#1a1a1a" },
  themeBtnText: { fontSize: 14, color: "#333" },
  themeBtnTextActive: { color: "#fff" },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  label: { fontSize: 15, color: "#333" },
  deleteBtn: { marginTop: "auto", padding: 16, alignItems: "center" },
  deleteText: { fontSize: 15, color: "#e53935" },
});
