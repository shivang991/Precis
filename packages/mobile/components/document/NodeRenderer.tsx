import React from "react";
import { View, Text, StyleSheet } from "react-native";
import type { DocumentContentTreeNodeOutput, HighlightRead } from "@precis/shared";
import { HighlightableText, TextSelection } from "./HighlightableText";

interface NodeRendererProps {
  nodes: DocumentContentTreeNodeOutput[];
  highlights: HighlightRead[];
  onSelectionChange: (sel: TextSelection) => void;
}

export function NodeRenderer({ nodes, highlights, onSelectionChange }: NodeRendererProps) {
  return (
    <>
      {nodes.map((node) => (
        <RenderNode
          key={node.id}
          node={node}
          highlights={highlights}
          onSelectionChange={onSelectionChange}
        />
      ))}
    </>
  );
}

function RenderNode({
  node,
  highlights,
  onSelectionChange,
}: {
  node: DocumentContentTreeNodeOutput;
  highlights: HighlightRead[];
  onSelectionChange: (sel: TextSelection) => void;
}) {
  const nodeHighlights = highlights.filter((h) => h.node_id === node.id);

  switch (node.type) {
    case "heading":
      return (
        <View style={styles.headingContainer}>
          <Text style={[styles.heading, node.level != null && headingStyles[node.level]]}>
            {node.text}
          </Text>
          {node.children && node.children.length > 0 && (
            <NodeRenderer
              nodes={node.children}
              highlights={highlights}
              onSelectionChange={onSelectionChange}
            />
          )}
        </View>
      );

    case "paragraph":
      return (
        <View style={styles.paragraphContainer}>
          <HighlightableText
            nodeId={node.id}
            text={node.text ?? ""}
            highlights={nodeHighlights}
            onSelectionChange={onSelectionChange}
          />
        </View>
      );

    case "list_item":
      return (
        <View style={[styles.listItem, { paddingLeft: ((node.content?.depth as number) ?? 0) * 16 + 8 }]}>
          <Text style={styles.bullet}>•</Text>
          <HighlightableText
            nodeId={node.id}
            text={node.text ?? ""}
            highlights={nodeHighlights}
            onSelectionChange={onSelectionChange}
          />
        </View>
      );

    case "table":
      return (
        <View style={styles.table}>
          <View style={styles.tableRow}>
            {((node.content?.headers as string[]) ?? []).map((h, i) => (
              <Text key={i} style={styles.tableHeader}>{h}</Text>
            ))}
          </View>
          {((node.content?.rows as string[][]) ?? []).map((row, ri) => (
            <View key={ri} style={styles.tableRow}>
              {row.map((cell, ci) => (
                <Text key={ci} style={styles.tableCell}>{cell}</Text>
              ))}
            </View>
          ))}
        </View>
      );

    case "code":
      return (
        <View style={styles.codeBlock}>
          <Text style={styles.codeText}>{node.text}</Text>
        </View>
      );

    default:
      return null;
  }
}

const headingStyles: Record<number, object> = {
  1: { fontSize: 26, fontWeight: "700", marginTop: 24, marginBottom: 8 },
  2: { fontSize: 22, fontWeight: "700", marginTop: 20, marginBottom: 6 },
  3: { fontSize: 18, fontWeight: "600", marginTop: 16, marginBottom: 4 },
  4: { fontSize: 16, fontWeight: "600", marginTop: 12, marginBottom: 4 },
  5: { fontSize: 14, fontWeight: "600", marginTop: 8, marginBottom: 2 },
  6: { fontSize: 13, fontWeight: "600", marginTop: 8, marginBottom: 2 },
};

const styles = StyleSheet.create({
  headingContainer: { marginBottom: 4 },
  heading: { color: "#1a1a1a" },
  paragraphContainer: { marginBottom: 12 },
  listItem: { flexDirection: "row", marginBottom: 6, alignItems: "flex-start" },
  bullet: { marginRight: 6, color: "#555", lineHeight: 22 },
  table: { marginVertical: 12, borderWidth: 1, borderColor: "#ddd", borderRadius: 4 },
  tableRow: { flexDirection: "row", borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: "#ddd" },
  tableHeader: { flex: 1, padding: 8, fontWeight: "600", fontSize: 13, backgroundColor: "#f5f5f5" },
  tableCell: { flex: 1, padding: 8, fontSize: 13 },
  codeBlock: { backgroundColor: "#f5f5f5", padding: 12, borderRadius: 6, marginVertical: 8 },
  codeText: { fontFamily: "monospace", fontSize: 13, color: "#333" },
});
