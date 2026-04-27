import React, { useMemo } from 'react';

import {
  View,
  ScrollView,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
} from 'react-native';

import { useLocalSearchParams, useRouter } from 'expo-router';

import { useQuery } from '@tanstack/react-query';

import type {
  DocumentContentTreeNodeOutput,
  TableHighlightRead,
  TextHighlightRead,
} from '@precis/shared';

type Highlight = TextHighlightRead | TableHighlightRead;

import { useApi } from '../../../../hooks/useApi';

export default function SummaryViewScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const api = useApi();

  const { data: document, isLoading: docLoading } = useQuery({
    queryKey: ['document', id],
    queryFn: () => api.getDocument(id),
    enabled: !!id,
  });

  const { data: highlights = [] as Highlight[], isLoading: hlLoading } = useQuery<Highlight[]>({
    queryKey: ['highlights', id],
    queryFn: () => api.listHighlights(id) as Promise<Highlight[]>,
    enabled: !!id && document?.status === 'ready',
  });

  const highlightsByNode = useMemo(() => {
    const map = new Map<string, Highlight[]>();
    for (const h of highlights) {
      const list = map.get(h.node_id);
      if (list) list.push(h);
      else map.set(h.node_id, [h]);
    }
    for (const list of map.values()) {
      list.sort((a, b) => {
        const sa = 'start_offset' in a ? (a.start_offset ?? 0) : 0;
        const sb = 'start_offset' in b ? (b.start_offset ?? 0) : 0;
        return sa - sb;
      });
    }
    return map;
  }, [highlights]);

  const nodes = document?.document_content_tree ?? [];
  const hasAnyHighlights = highlights.length > 0;

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
        {!hasAnyHighlights ? (
          <Text style={styles.empty}>
            No highlights yet. Go back and highlight passages to build your summary.
          </Text>
        ) : (
          nodes.map((n) => <RenderNode key={n.id} node={n} highlightsByNode={highlightsByNode} />)
        )}
      </ScrollView>
    </View>
  );
}

// Returns true if this subtree contains any highlights.
function subtreeHasHighlights(
  node: DocumentContentTreeNodeOutput,
  highlightsByNode: Map<string, Highlight[]>,
): boolean {
  if (highlightsByNode.has(node.id)) return true;
  if (node.children) {
    for (const c of node.children) {
      if (subtreeHasHighlights(c, highlightsByNode)) return true;
    }
  }
  return false;
}

function RenderNode({
  node,
  highlightsByNode,
}: {
  node: DocumentContentTreeNodeOutput;
  highlightsByNode: Map<string, Highlight[]>;
}) {
  if (!subtreeHasHighlights(node, highlightsByNode)) return null;

  const nodeHighlights = highlightsByNode.get(node.id);
  const content = node.content;

  switch (content.type) {
    case 'table': {
      const tableHls = (nodeHighlights ?? []).filter(
        (h): h is TableHighlightRead => h.type === 'table',
      );
      if (tableHls.length === 0) return null;
      const headers = (content.headers ?? []) as unknown[];
      return (
        <View style={styles.paragraphContainer}>
          {tableHls.map((h) => (
            <View key={h.id} style={styles.tablePreview}>
              <Text style={styles.tablePreviewLabel}>Table highlight</Text>
              <Text style={styles.tablePreviewText}>
                {h.rows.length > 0 ? `Rows: ${h.rows.map((r) => r + 1).join(', ')}` : null}
                {h.rows.length > 0 && h.columns.length > 0 ? '  ·  ' : null}
                {h.columns.length > 0
                  ? `Cols: ${h.columns
                      .map((c) => (headers[c] != null ? String(headers[c]) : `${c + 1}`))
                      .join(', ')}`
                  : null}
              </Text>
            </View>
          ))}
        </View>
      );
    }
    case 'text': {
      if (content.level != null) {
        const level = content.level;
        const typo = headingTypography[level] ?? headingTypography[1];
        return (
          <View style={[styles.headingContainer, headingSpacing[level] ?? headingSpacing[1]]}>
            <Text
              style={[{ fontSize: typo.fontSize, lineHeight: typo.lineHeight }, styles.heading]}
            >
              {content.text}
            </Text>
            {node.children?.map((c) => (
              <RenderNode key={c.id} node={c} highlightsByNode={highlightsByNode} />
            ))}
          </View>
        );
      }
      const textHls = (nodeHighlights ?? []).filter(
        (h): h is TextHighlightRead => h.type !== 'table',
      );
      return textHls.length > 0 ? (
        <View style={styles.paragraphContainer}>
          <HighlightedSpans text={content.text} highlights={textHls} />
        </View>
      ) : null;
    }

    default:
      return null;
  }
}

// Renders each highlighted span as its own Text. Spans from the same node
// are shown on separate lines so the reader sees distinct picks rather than
// a single mashed-together fragment.
function HighlightedSpans({ text, highlights }: { text: string; highlights: TextHighlightRead[] }) {
  return (
    <View style={styles.spans}>
      {highlights.map((h) => (
        <Text key={h.id} style={styles.highlighted}>
          {text.substring(h.start_offset!, h.end_offset!)}
        </Text>
      ))}
    </View>
  );
}

const headingTypography: Record<number, { fontSize: number; lineHeight: number }> = {
  1: { fontSize: 26, lineHeight: 34 },
  2: { fontSize: 22, lineHeight: 30 },
  3: { fontSize: 18, lineHeight: 26 },
  4: { fontSize: 16, lineHeight: 24 },
  5: { fontSize: 14, lineHeight: 22 },
  6: { fontSize: 13, lineHeight: 20 },
};

const headingSpacing: Record<number, ViewStyle> = {
  1: { marginTop: 24, marginBottom: 8 },
  2: { marginTop: 20, marginBottom: 6 },
  3: { marginTop: 16, marginBottom: 4 },
  4: { marginTop: 12, marginBottom: 4 },
  5: { marginTop: 8, marginBottom: 2 },
  6: { marginTop: 8, marginBottom: 2 },
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  toolbar: {
    flexDirection: 'row',
    gap: 8,
    padding: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#e0e0e0',
  },
  toolBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ccc',
  },
  toolBtnText: { fontSize: 13, color: '#333' },
  scroll: { flex: 1 },
  content: { padding: 16, paddingBottom: 48 },
  headingContainer: {},
  heading: { fontWeight: '700', color: '#1a1a1a' },
  paragraphContainer: { marginBottom: 12 },
  spans: { gap: 4 },
  highlighted: {
    fontSize: 15,
    lineHeight: 24,
    color: '#1a1a1a',
    backgroundColor: '#FFF176',
    borderRadius: 3,
    paddingHorizontal: 2,
  },
  empty: { textAlign: 'center', color: '#999', marginTop: 64, lineHeight: 24 },
  tablePreview: {
    borderLeftWidth: 3,
    borderLeftColor: '#FFC107',
    paddingLeft: 10,
    paddingVertical: 4,
    marginBottom: 6,
  },
  tablePreviewLabel: {
    fontSize: 11,
    color: '#999',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  tablePreviewText: { fontSize: 14, color: '#1a1a1a', lineHeight: 20 },
});
