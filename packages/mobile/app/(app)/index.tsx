import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as DocumentPicker from "expo-document-picker";
import type { DocumentRead } from "@precis/shared";
import { useApi } from "../../hooks/useApi";

export default function FilesListScreen() {
  const router = useRouter();
  const api = useApi();
  const qc = useQueryClient();

  const { data: documents, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(),
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const result = await DocumentPicker.getDocumentAsync({
        type: "application/pdf",
        copyToCacheDirectory: true,
      });
      if (result.canceled) return;

      const asset = result.assets[0];
      // React Native FormData accepts {uri, name, type} objects in place of Blob
      const file = {
        uri: asset.uri,
        name: asset.name,
        type: "application/pdf",
      } as unknown as Blob;
      return api.uploadDocument({ file });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
    onError: (e: any) => Alert.alert("Upload failed", e.message),
  });

  const renderItem = ({ item }: { item: DocumentRead }) => (
    <TouchableOpacity
      style={styles.row}
      onPress={() => router.push(`/(app)/documents/${item.id}`)}
    >
      <View style={styles.rowContent}>
        <Text style={styles.docTitle} numberOfLines={1}>
          {item.title}
        </Text>
        <Text style={styles.docMeta}>
          {item.source} · {item.status}
        </Text>
      </View>
      <Text style={styles.openLabel}>Open</Text>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.heading}>Your Files</Text>
        <View style={styles.headerActions}>
          <TouchableOpacity
            style={styles.settingsBtn}
            onPress={() => router.push("/(app)/settings")}
          >
            <Text style={styles.settingsBtnText}>General Settings</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.addBtn}
            onPress={() => uploadMutation.mutate()}
            disabled={uploadMutation.isPending}
          >
            {uploadMutation.isPending ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={styles.addBtnText}>+</Text>
            )}
          </TouchableOpacity>
        </View>
      </View>

      {isLoading ? (
        <ActivityIndicator style={{ marginTop: 48 }} />
      ) : (
        <FlatList
          data={documents}
          keyExtractor={(d) => d.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <Text style={styles.empty}>No documents yet. Tap + to upload.</Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#e0e0e0",
  },
  heading: { fontSize: 22, fontWeight: "700" },
  headerActions: { flexDirection: "row", alignItems: "center", gap: 8 },
  settingsBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 8,
  },
  settingsBtnText: { fontSize: 13, color: "#333" },
  addBtn: {
    width: 36,
    height: 36,
    backgroundColor: "#1a1a1a",
    borderRadius: 8,
    justifyContent: "center",
    alignItems: "center",
  },
  addBtnText: { color: "#fff", fontSize: 22, lineHeight: 28 },
  list: { padding: 16, gap: 2 },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#e0e0e0",
  },
  rowContent: { flex: 1, marginRight: 12 },
  docTitle: { fontSize: 15, fontWeight: "500" },
  docMeta: { fontSize: 12, color: "#888", marginTop: 2 },
  openLabel: { fontSize: 14, color: "#1a73e8", fontWeight: "500" },
  empty: { textAlign: "center", color: "#999", marginTop: 48 },
});
