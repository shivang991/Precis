import React from "react";
import {
  View,
  ScrollView,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Share,
} from "react-native";
import { useLocalSearchParams, useRouter, useNavigation } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useApi } from "../../../hooks/useApi";
import { useDocumentStore } from "../../../store/document";
import { NodeRenderer } from "../../../components/document/NodeRenderer";
import type { HighlightCreate } from "@precis/shared";

const COLORS = ["yellow", "green", "blue", "pink", "purple"];

export default function DocumentViewerScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const api = useApi();
  const qc = useQueryClient();
  const { highlightMode, activeColor, setHighlightMode, setActiveColor } = useDocumentStore();

  const { data: document, isLoading: docLoading } = useQuery({
    queryKey: ["document", id],
    queryFn: () => api.getDocument(id),
    enabled: !!id,
  });

  const { data: highlights = [] } = useQuery({
    queryKey: ["highlights", id],
    queryFn: () => api.listHighlights(id),
    enabled: !!id && document?.status === "READY",
  });

  const createHighlight = useMutation({
    mutationFn: (data: HighlightCreate) => api.createHighlight(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["highlights", id] }),
    onError: (e: any) => Alert.alert("Highlight failed", e.message),
  });

  const handleSelect = (nodeId: string, start: number, end: number) => {
    createHighlight.mutate({ node_id: nodeId, start_offset: start, end_offset: end, color: activeColor });
  };

  if (docLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!document) {
    return (
      <View style={styles.center}>
        <Text>Document not found.</Text>
      </View>
    );
  }

  if (document.status !== "READY") {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text style={styles.processingText}>Processing document…</Text>
      </View>
    );
  }

  const nodes = document.document_content_tree?.nodes ?? [];

  return (
    <View style={styles.container}>
      {/* Toolbar */}
      <View style={styles.toolbar}>
        <TouchableOpacity
          style={[styles.toolBtn, highlightMode === "highlight" && styles.toolBtnActive]}
          onPress={() => setHighlightMode(highlightMode === "view" ? "highlight" : "view")}
        >
          <Text style={[styles.toolBtnText, highlightMode === "highlight" && styles.toolBtnTextActive]}>
            {highlightMode === "highlight" ? "Highlighting" : "Highlight"}
          </Text>
        </TouchableOpacity>

        {highlightMode === "highlight" && (
          <View style={styles.colorPicker}>
            {COLORS.map((c) => (
              <TouchableOpacity
                key={c}
                style={[styles.colorDot, { backgroundColor: colorHex(c) }, activeColor === c && styles.colorDotActive]}
                onPress={() => setActiveColor(c)}
              />
            ))}
          </View>
        )}

        <TouchableOpacity
          style={styles.toolBtn}
          onPress={() => router.push(`/(app)/documents/${id}/summary`)}
        >
          <Text style={styles.toolBtnText}>Summary</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.toolBtn}
          onPress={() => router.push(`/(app)/documents/${id}/settings`)}
        >
          <Text style={styles.toolBtnText}>Settings</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        <NodeRenderer
          nodes={nodes}
          highlights={highlights}
          highlightMode={highlightMode === "highlight"}
          activeColor={activeColor}
          onCreateHighlight={handleSelect}
        />
      </ScrollView>
    </View>
  );
}

function colorHex(c: string): string {
  const map: Record<string, string> = {
    yellow: "#FFF176", green: "#C8E6C9", blue: "#BBDEFB", pink: "#F8BBD0", purple: "#E1BEE7",
  };
  return map[c] ?? "#FFF176";
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  processingText: { marginTop: 12, color: "#666" },
  toolbar: {
    flexDirection: "row",
    alignItems: "center",
    padding: 8,
    gap: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#e0e0e0",
    flexWrap: "wrap",
  },
  toolBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#ccc",
  },
  toolBtnActive: { backgroundColor: "#1a1a1a", borderColor: "#1a1a1a" },
  toolBtnText: { fontSize: 13, color: "#333" },
  toolBtnTextActive: { color: "#fff" },
  colorPicker: { flexDirection: "row", gap: 6, alignItems: "center" },
  colorDot: { width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: "transparent" },
  colorDotActive: { borderColor: "#333" },
  scroll: { flex: 1 },
  content: { padding: 16, paddingBottom: 48 },
});
