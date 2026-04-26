import React from 'react';

import { View, Text, StyleSheet, TouchableOpacity, ViewStyle } from 'react-native';

import type {
  DocumentContentTreeNodeOutput,
  ImageHighlightRead,
  TableHighlightRead,
  TextHighlightRead,
} from '@precis/shared';

import { HighlightableText } from './HighlightableText';

export type Highlight = TextHighlightRead | TableHighlightRead | ImageHighlightRead;

interface NodeRendererProps {
  nodes: DocumentContentTreeNodeOutput[];
  highlights: Highlight[];
  onToggleTableHeader?: (nodeId: string, kind: 'row' | 'column', index: number) => void;
  onToggleImage?: (nodeId: string) => void;
}

export function NodeRenderer({
  nodes,
  highlights,
  onToggleTableHeader,
  onToggleImage,
}: NodeRendererProps) {
  return (
    <>
      {nodes.map((node) => (
        <RenderNode
          key={node.id}
          node={node}
          highlights={highlights}
          onToggleTableHeader={onToggleTableHeader}
          onToggleImage={onToggleImage}
        />
      ))}
    </>
  );
}

function isTextHighlight(h: Highlight): h is TextHighlightRead {
  return h.type === 'text' || h.type === undefined;
}

function isTableHighlight(h: Highlight): h is TableHighlightRead {
  return h.type === 'table';
}

function isImageHighlight(h: Highlight): h is ImageHighlightRead {
  return h.type === 'image';
}

function RenderNode({
  node,
  highlights,
  onToggleTableHeader,
  onToggleImage,
}: {
  node: DocumentContentTreeNodeOutput;
  highlights: Highlight[];
  onToggleTableHeader?: (nodeId: string, kind: 'row' | 'column', index: number) => void;
  onToggleImage?: (nodeId: string) => void;
}) {
  const content = node.content;

  switch (content.type) {
    case 'text': {
      const nodeTextHighlights = highlights
        .filter(isTextHighlight)
        .filter((h) => h.node_id === node.id);
      if (content.level != null) {
        const level = content.level;
        const typo = headingTypography[level] ?? headingTypography[1];
        return (
          <View style={[styles.headingContainer, headingSpacing[level] ?? headingSpacing[1]]}>
            <HighlightableText
              nodeId={node.id}
              text={content.text}
              highlights={nodeTextHighlights}
              fontSize={typo.fontSize}
              lineHeight={typo.lineHeight}
              bold
            />
            {node.children && node.children.length > 0 && (
              <NodeRenderer
                nodes={node.children}
                highlights={highlights}
                onToggleTableHeader={onToggleTableHeader}
                onToggleImage={onToggleImage}
              />
            )}
          </View>
        );
      }
      return (
        <View style={styles.paragraphContainer}>
          <HighlightableText nodeId={node.id} text={content.text} highlights={nodeTextHighlights} />
        </View>
      );
    }

    case 'table': {
      const headers = (content.headers ?? []) as unknown[];
      const rows = (content.rows ?? []) as unknown[][];
      const tableHighlights = highlights
        .filter(isTableHighlight)
        .filter((h) => h.node_id === node.id);
      const highlightedRows = new Set<number>(tableHighlights.flatMap((h) => h.rows));
      const highlightedCols = new Set<number>(tableHighlights.flatMap((h) => h.columns));
      const cellIsHighlighted = (ri: number, ci: number) =>
        highlightedRows.has(ri) || highlightedCols.has(ci);

      return (
        <View style={styles.table}>
          {headers.length > 0 && (
            <View style={styles.tableRow}>
              <View style={[styles.rowIndexHeader]} />
              {headers.map((h, ci) => (
                <TouchableOpacity
                  key={ci}
                  onPress={() => onToggleTableHeader?.(node.id, 'column', ci)}
                  activeOpacity={0.7}
                  style={[
                    styles.tableHeader,
                    highlightedCols.has(ci) ? styles.headerSelected : null,
                  ]}
                >
                  <Text style={styles.tableHeaderText}>{String(h ?? '')}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
          {rows.map((row, ri) => (
            <View key={ri} style={styles.tableRow}>
              <TouchableOpacity
                onPress={() => onToggleTableHeader?.(node.id, 'row', ri)}
                activeOpacity={0.7}
                style={[
                  styles.rowIndexCell,
                  highlightedRows.has(ri) ? styles.headerSelected : null,
                ]}
              >
                <Text style={styles.rowIndexText}>{ri + 1}</Text>
              </TouchableOpacity>
              {row.map((cell, ci) => (
                <View
                  key={ci}
                  style={[
                    styles.tableCell,
                    cellIsHighlighted(ri, ci) ? styles.cellHighlighted : null,
                  ]}
                >
                  <Text style={styles.tableCellText}>{String(cell ?? '')}</Text>
                </View>
              ))}
            </View>
          ))}
        </View>
      );
    }

    case 'image': {
      const isHighlighted = highlights.filter(isImageHighlight).some((h) => h.node_id === node.id);
      const alt = content.alt ?? 'Image';
      return (
        <TouchableOpacity
          activeOpacity={0.7}
          onPress={() => onToggleImage?.(node.id)}
          style={[styles.imageWrapper, isHighlighted ? styles.imageWrapperHighlighted : null]}
        >
          <Text style={styles.imagePlaceholderLabel}>IMAGE</Text>
          <Text style={styles.imagePlaceholderAlt}>{alt}</Text>
        </TouchableOpacity>
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

const ROW_INDEX_WIDTH = 28;

const styles = StyleSheet.create({
  headingContainer: {},
  paragraphContainer: { marginBottom: 12 },
  table: { marginVertical: 12, borderWidth: 1, borderColor: '#ddd', borderRadius: 4 },
  tableRow: {
    flexDirection: 'row',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#ddd',
  },
  tableHeader: { flex: 1, padding: 8, backgroundColor: '#f5f5f5' },
  tableHeaderText: { fontWeight: '600', fontSize: 13 },
  tableCell: { flex: 1, padding: 8 },
  tableCellText: { fontSize: 13 },
  cellHighlighted: { backgroundColor: '#FFF176' },
  rowIndexHeader: {
    width: ROW_INDEX_WIDTH,
    backgroundColor: '#f5f5f5',
  },
  rowIndexCell: {
    width: ROW_INDEX_WIDTH,
    padding: 8,
    backgroundColor: '#fafafa',
    alignItems: 'center',
  },
  rowIndexText: { fontSize: 11, color: '#888', fontWeight: '600' },
  headerSelected: { backgroundColor: '#FFE082' },
  imageWrapper: {
    marginVertical: 12,
    paddingVertical: 24,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 6,
    backgroundColor: '#fafafa',
    alignItems: 'center',
  },
  imageWrapperHighlighted: {
    backgroundColor: '#FFF8C4',
    borderColor: '#FFC107',
    borderWidth: 2,
  },
  imagePlaceholderLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: '#999',
    letterSpacing: 1,
    marginBottom: 4,
  },
  imagePlaceholderAlt: { fontSize: 13, color: '#555' },
});
