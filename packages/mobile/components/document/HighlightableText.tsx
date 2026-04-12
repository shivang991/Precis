import React, { useRef } from "react";
import { Text, StyleSheet, Platform } from "react-native";
import type { HighlightRead } from "@precis/shared";

const HIGHLIGHT_COLORS: Record<string, string> = {
  yellow: "#FFF176",
  green: "#C8E6C9",
  blue: "#BBDEFB",
  pink: "#F8BBD0",
  purple: "#E1BEE7",
};

interface HighlightableTextProps {
  nodeId: string;
  text: string;
  highlights: HighlightRead[];
  highlightMode: boolean;
  activeColor: string;
  onSelect: (nodeId: string, start: number, end: number) => void;
}

/**
 * Renders a text node with existing highlights shown as colored spans.
 * When highlightMode is active, the native text selection handles are used
 * to capture the selection range on selection end.
 */
export function HighlightableText({
  nodeId,
  text,
  highlights,
  highlightMode,
  activeColor,
  onSelect,
}: HighlightableTextProps) {
  const selectionRef = useRef<{ start: number; end: number } | null>(null);

  // Build segments: merge highlight ranges into colored spans
  const segments = buildSegments(text, highlights);

  if (!highlightMode) {
    return (
      <Text style={styles.text} selectable={false}>
        {segments.map((seg, i) =>
          seg.color ? (
            <Text key={i} style={{ backgroundColor: HIGHLIGHT_COLORS[seg.color] ?? "#FFF176" }}>
              {seg.text}
            </Text>
          ) : (
            <Text key={i}>{seg.text}</Text>
          )
        )}
      </Text>
    );
  }

  return (
    <Text
      style={styles.text}
      selectable
      onSelectionChange={(e) => {
        const { start, end } = e.nativeEvent.selection;
        if (start !== end) {
          selectionRef.current = { start, end };
        }
      }}
      // On iOS/Android, fire highlight creation when user lifts finger after selection.
      // We use onPress as a proxy — the selection change fires before the press.
      onPress={() => {
        const sel = selectionRef.current;
        if (sel && sel.start !== sel.end) {
          onSelect(nodeId, sel.start, sel.end);
          selectionRef.current = null;
        }
      }}
    >
      {segments.map((seg, i) =>
        seg.color ? (
          <Text key={i} style={{ backgroundColor: HIGHLIGHT_COLORS[seg.color] ?? "#FFF176" }}>
            {seg.text}
          </Text>
        ) : (
          <Text key={i}>{seg.text}</Text>
        )
      )}
    </Text>
  );
}

interface Segment {
  text: string;
  color?: string;
}

function buildSegments(text: string, highlights: HighlightRead[]): Segment[] {
  if (highlights.length === 0) return [{ text }];

  // Build a list of [start, end, color] ranges, sorted by start
  const ranges = highlights
    .filter((h) => h.start_offset != null && h.end_offset != null)
    .map((h) => ({ start: h.start_offset!, end: h.end_offset!, color: "yellow" }))
    .sort((a, b) => a.start - b.start);

  if (ranges.length === 0) {
    // Node-level highlight (no offsets) — highlight the whole text
    return [{ text, color: "yellow" }];
  }

  const segments: Segment[] = [];
  let cursor = 0;

  for (const range of ranges) {
    if (range.start > cursor) {
      segments.push({ text: text.slice(cursor, range.start) });
    }
    segments.push({ text: text.slice(range.start, range.end), color: range.color });
    cursor = range.end;
  }

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor) });
  }

  return segments;
}

const styles = StyleSheet.create({
  text: {
    fontSize: 15,
    lineHeight: 24,
    color: "#1a1a1a",
  },
});
