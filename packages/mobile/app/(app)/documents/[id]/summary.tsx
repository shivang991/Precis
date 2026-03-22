import React from "react";
import {
  View,
  ScrollView,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Share,
  Alert,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { useApi } from "../../../../hooks/useApi";
import type { SummarySection } from "@precis/shared";

const HIGHLIGHT_COLORS: Record<string, string> = {
  yellow: "#FFF176", green: "#C8E6C9", blue: "#BBDEFB", pink: "#F8BBD0", purple: "#E1BEE7",
};

export default function SummaryViewScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const api = useApi();

  const { data: summary, isLoading } = useQuery({
    queryKey: ["summary", id],
    queryFn: () => api.getSummary(id),
    enabled: !!id,
  });

  const handleExport = async () => {
    try {
      const blob = await api.exportSummaryPdf(id);
      Alert.alert("Export", "PDF export is available — save via share sheet once file handling is wired up.");
    } catch (e: any) {
      Alert.alert("Export failed", e.message);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Toolbar */}
      <View style={styles.toolbar}>
        <TouchableOpacity style={styles.toolBtn} onPress={handleExport}>
          <Text style={styles.toolBtnText}>Export PDF</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.toolBtn}
          onPress={() => router.back()}
        >
          <Text style={styles.toolBtnText}>View Original</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        {(!summary || summary.length === 0) ? (
          <Text style={styles.empty}>No highlights yet. Go back and highlight passages to build your summary.</Text>
        ) : (
          summary.map((section) => (
            <SummarySectionCard key={section.highlight_id} section={section} />
          ))
        )}
      </ScrollView>
    </View>
  );
}

function SummarySectionCard({ section }: { section: SummarySection }) {
  return (
    <View style={styles.card}>
      {section.ancestors.length > 0 && (
        <View style={styles.breadcrumb}>
          {section.ancestors.map((a: any, i: number) => (
            <React.Fragment key={a.node_id}>
              {i > 0 && <Text style={styles.breadcrumbSep}> › </Text>}
              <Text style={[styles.breadcrumbItem, { fontSize: 13 - (a.level ?? 1) }]}>
                {a.text}
              </Text>
            </React.Fragment>
          ))}
        </View>
      )}
      <Text
        style={[
          styles.highlightedText,
          { backgroundColor: HIGHLIGHT_COLORS[section.color] ?? "#FFF176" },
        ]}
      >
        {section.text}
      </Text>
      {section.note && <Text style={styles.note}>{section.note}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  toolbar: {
    flexDirection: "row",
    gap: 8,
    padding: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#e0e0e0",
  },
  toolBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#ccc",
  },
  toolBtnText: { fontSize: 13, color: "#333" },
  scroll: { flex: 1 },
  content: { padding: 16, gap: 16, paddingBottom: 48 },
  card: {
    borderLeftWidth: 3,
    borderLeftColor: "#1a1a1a",
    paddingLeft: 12,
    paddingVertical: 8,
  },
  breadcrumb: { flexDirection: "row", flexWrap: "wrap", marginBottom: 6 },
  breadcrumbItem: { fontWeight: "600", color: "#555" },
  breadcrumbSep: { color: "#aaa" },
  highlightedText: { fontSize: 15, lineHeight: 24, color: "#1a1a1a", borderRadius: 3, paddingHorizontal: 2 },
  note: { marginTop: 6, fontSize: 13, color: "#888", fontStyle: "italic" },
  empty: { textAlign: "center", color: "#999", marginTop: 64, lineHeight: 24 },
});
