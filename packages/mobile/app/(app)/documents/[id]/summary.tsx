import React, { useMemo } from "react";
import {
  View,
  ScrollView,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { useApi } from "../../../../hooks/useApi";
import type {
  DocumentContentTreeNodeOutput,
  HighlightRead,
} from "@precis/shared";

interface HeadingCrumb {
  node_id: string;
  text: string;
  level: number;
}

interface SummarySection {
  highlight_id: string;
  text: string;
  ancestors: HeadingCrumb[];
}

export default function SummaryViewScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const api = useApi();

  const { data: document, isLoading: docLoading } = useQuery({
    queryKey: ["document", id],
    queryFn: () => api.getDocument(id),
    enabled: !!id,
  });

  const { data: highlights = [], isLoading: hlLoading } = useQuery({
    queryKey: ["highlights", id],
    queryFn: () => api.listHighlights(id),
    enabled: !!id && document?.status === "ready",
  });

  const sections = useMemo<SummarySection[]>(() => {
    const nodes = document?.document_content_tree?.nodes ?? [];
    if (nodes.length === 0 || highlights.length === 0) return [];
    return buildSummary(nodes, highlights);
  }, [document, highlights]);

  if (docLoading || hlLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.toolbar}>
        <TouchableOpacity style={styles.toolBtn} onPress={() => router.back()}>
          <Text style={styles.toolBtnText}>View Original</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        {sections.length === 0 ? (
          <Text style={styles.empty}>
            No highlights yet. Go back and highlight passages to build your summary.
          </Text>
        ) : (
          sections.map((section) => (
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
          {section.ancestors.map((a, i) => (
            <React.Fragment key={a.node_id}>
              {i > 0 && <Text style={styles.breadcrumbSep}> › </Text>}
              <Text style={styles.breadcrumbItem}>{a.text}</Text>
            </React.Fragment>
          ))}
        </View>
      )}
      <Text style={styles.highlightedText}>{section.text}</Text>
    </View>
  );
}

// Walks the content tree in document order. Maintains a stack of open
// headings (by level) so each highlight gets the path of headings that
// currently scope it.
function buildSummary(
  nodes: DocumentContentTreeNodeOutput[],
  highlights: HighlightRead[],
): SummarySection[] {
  const byNode = new Map<string, HighlightRead[]>();
  for (const h of highlights) {
    if (h.start_offset == null || h.end_offset == null) continue;
    const list = byNode.get(h.node_id);
    if (list) list.push(h);
    else byNode.set(h.node_id, [h]);
  }

  const out: SummarySection[] = [];
  const headingStack: HeadingCrumb[] = [];

  const visit = (node: DocumentContentTreeNodeOutput) => {
    if (node.type === "heading") {
      const level = node.level ?? 1;
      while (
        headingStack.length > 0 &&
        headingStack[headingStack.length - 1].level >= level
      ) {
        headingStack.pop();
      }
      headingStack.push({ node_id: node.id, text: node.text ?? "", level });
      if (node.children) for (const child of node.children) visit(child);
      // Pop this heading when leaving its subtree.
      const idx = headingStack.findIndex((h) => h.node_id === node.id);
      if (idx >= 0) headingStack.length = idx;
      return;
    }

    const hs = byNode.get(node.id);
    if (hs && node.text) {
      const text = node.text;
      const ancestors = headingStack.slice();
      const sorted = hs
        .slice()
        .sort((a, b) => (a.start_offset ?? 0) - (b.start_offset ?? 0));
      for (const h of sorted) {
        out.push({
          highlight_id: h.id,
          text: text.substring(h.start_offset!, h.end_offset!),
          ancestors,
        });
      }
    }

    if (node.children) for (const child of node.children) visit(child);
  };

  for (const node of nodes) visit(node);
  return out;
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
  breadcrumbItem: { fontWeight: "600", color: "#555", fontSize: 12 },
  breadcrumbSep: { color: "#aaa", fontSize: 12 },
  highlightedText: {
    fontSize: 15,
    lineHeight: 24,
    color: "#1a1a1a",
    backgroundColor: "#FFF176",
    borderRadius: 3,
    paddingHorizontal: 2,
  },
  empty: { textAlign: "center", color: "#999", marginTop: 64, lineHeight: 24 },
});
