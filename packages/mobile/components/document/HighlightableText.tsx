import React, { useState } from "react";
import { Text, TextInput, StyleSheet } from "react-native";
import type { HighlightRead } from "@precis/shared";

const HIGHLIGHT_YELLOW = "#FFF176";

export interface TextSelection {
  nodeId: string;
  start: number;
  end: number;
}

interface HighlightableTextProps {
  nodeId: string;
  text: string;
  highlights: HighlightRead[];
  onSelectionChange: (sel: TextSelection) => void;
}

export function HighlightableText({
  nodeId,
  text,
  highlights,
  onSelectionChange,
}: HighlightableTextProps) {
  const [controlledSelection, setControlledSelection] = useState<
    { start: number; end: number } | undefined
  >(undefined);
  const [activeSelection, setActiveSelection] = useState<
    { start: number; end: number } | null
  >(null);

  const segments = buildSegments(text, highlights, activeSelection);

  const handleSelectionChange = (e: {
    nativeEvent: { selection: { start: number; end: number } };
  }) => {
    const { start, end } = e.nativeEvent.selection;
    if (start === end) {
      const hit = findHighlightAt(highlights, start);
      if (hit) {
        const expanded = { start: hit.start_offset!, end: hit.end_offset! };
        setControlledSelection(expanded);
        return;
      }
      setActiveSelection(null);
      setControlledSelection(undefined);
      onSelectionChange({ nodeId, start, end });
      return;
    }
    setActiveSelection({ start, end });
    setControlledSelection(undefined);
    onSelectionChange({ nodeId, start, end });
  };

  return (
    <TextInput
      multiline
      scrollEnabled={false}
      showSoftInputOnFocus={false}
      caretHidden
      spellCheck={false}
      autoCorrect={false}
      selection={controlledSelection}
      style={[styles.text, styles.input]}
      onSelectionChange={handleSelectionChange}
    >
      {segments.map((seg, i) =>
        seg.highlighted ? (
          <Text key={i} style={styles.highlighted}>
            {seg.text}
          </Text>
        ) : (
          <Text key={i}>{seg.text}</Text>
        ),
      )}
    </TextInput>
  );
}

interface Segment {
  text: string;
  start: number;
  end: number;
  highlighted?: boolean;
}

function buildSegments(
  text: string,
  highlights: HighlightRead[],
  selection: { start: number; end: number } | null,
): Segment[] {
  const ranges = highlights
    .filter((h) => h.start_offset != null && h.end_offset != null)
    .map((h) => ({ start: h.start_offset!, end: h.end_offset! }));

  const sel =
    selection && selection.start !== selection.end
      ? {
          start: Math.min(selection.start, selection.end),
          end: Math.max(selection.start, selection.end),
        }
      : null;

  const clamp = (n: number) => Math.max(0, Math.min(text.length, n));
  const boundaries = new Set<number>([0, text.length]);
  for (const r of ranges) {
    boundaries.add(clamp(r.start));
    boundaries.add(clamp(r.end));
  }
  if (sel) {
    boundaries.add(clamp(sel.start));
    boundaries.add(clamp(sel.end));
  }
  const points = [...boundaries].sort((a, b) => a - b);

  const inHighlight = (lo: number, hi: number) =>
    ranges.some((r) => r.start < hi && r.end > lo);
  const inSelection = (lo: number, hi: number) =>
    !!sel && sel.start < hi && sel.end > lo;

  const out: Segment[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const lo = points[i];
    const hi = points[i + 1];
    if (lo === hi) continue;
    const highlighted = inHighlight(lo, hi) && !inSelection(lo, hi);
    out.push({
      text: text.slice(lo, hi),
      start: lo,
      end: hi,
      highlighted: highlighted || undefined,
    });
  }
  return out;
}

function findHighlightAt(highlights: HighlightRead[], pos: number): HighlightRead | undefined {
  return highlights.find(
    (h) =>
      h.start_offset != null &&
      h.end_offset != null &&
      pos >= h.start_offset &&
      pos <= h.end_offset,
  );
}

const styles = StyleSheet.create({
  text: {
    fontSize: 15,
    lineHeight: 24,
    color: "#1a1a1a",
  },
  input: {
    padding: 0,
    margin: 0,
  },
  highlighted: {
    backgroundColor: HIGHLIGHT_YELLOW,
  },
});
