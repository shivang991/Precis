import React from 'react';

import { View, Text, StyleSheet, ViewStyle } from 'react-native';

import type { DocumentContentTreeNodeOutput, HighlightRead } from '@precis/shared';

import { HighlightableText } from './HighlightableText';

interface NodeRendererProps {
  nodes: DocumentContentTreeNodeOutput[];
  highlights: HighlightRead[];
}

export function NodeRenderer({ nodes, highlights }: NodeRendererProps) {
  return (
    <>
      {nodes.map((node) => (
        <RenderNode key={node.id} node={node} highlights={highlights} />
      ))}
    </>
  );
}

function RenderNode({
  node,
  highlights,
}: {
  node: DocumentContentTreeNodeOutput;
  highlights: HighlightRead[];
}) {
  const nodeHighlights = highlights.filter((h) => h.node_id === node.id);
  const content = node.content;

  switch (content.type) {
    case 'text': {
      if (content.level != null) {
        const level = content.level;
        const typo = headingTypography[level] ?? headingTypography[1];
        return (
          <View style={[styles.headingContainer, headingSpacing[level] ?? headingSpacing[1]]}>
            <HighlightableText
              nodeId={node.id}
              text={content.text}
              highlights={nodeHighlights}
              fontSize={typo.fontSize}
              lineHeight={typo.lineHeight}
              bold
            />
            {node.children && node.children.length > 0 && (
              <NodeRenderer nodes={node.children} highlights={highlights} />
            )}
          </View>
        );
      }
      return (
        <View style={styles.paragraphContainer}>
          <HighlightableText nodeId={node.id} text={content.text} highlights={nodeHighlights} />
        </View>
      );
    }

    case 'table': {
      const headers = (content.headers ?? []) as unknown[];
      const rows = (content.rows ?? []) as unknown[][];
      return (
        <View style={styles.table}>
          {headers.length > 0 && (
            <View style={styles.tableRow}>
              {headers.map((h, i) => (
                <Text key={i} style={styles.tableHeader}>
                  {String(h ?? '')}
                </Text>
              ))}
            </View>
          )}
          {rows.map((row, ri) => (
            <View key={ri} style={styles.tableRow}>
              {row.map((cell, ci) => (
                <Text key={ci} style={styles.tableCell}>
                  {String(cell ?? '')}
                </Text>
              ))}
            </View>
          ))}
        </View>
      );
    }

    default:
      return null;
  }
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
  headingContainer: {},
  paragraphContainer: { marginBottom: 12 },
  table: { marginVertical: 12, borderWidth: 1, borderColor: '#ddd', borderRadius: 4 },
  tableRow: {
    flexDirection: 'row',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#ddd',
  },
  tableHeader: { flex: 1, padding: 8, fontWeight: '600', fontSize: 13, backgroundColor: '#f5f5f5' },
  tableCell: { flex: 1, padding: 8, fontSize: 13 },
});
