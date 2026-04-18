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

  const segments = applySelectionMask(buildSegments(text, highlights), activeSelection);

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

function buildSegments(text: string, highlights: HighlightRead[]): Segment[] {
  if (highlights.length === 0) return [{ text, start: 0, end: text.length }];

  const ranges = highlights
    .filter((h) => h.start_offset != null && h.end_offset != null)
    .map((h) => ({ start: h.start_offset!, end: h.end_offset! }))
    .sort((a, b) => a.start - b.start);

  if (ranges.length === 0) {
    return [{ text, start: 0, end: text.length, highlighted: true }];
  }

  const segments: Segment[] = [];
  let cursor = 0;
  for (const range of ranges) {
    if (range.start > cursor) {
      segments.push({ text: text.slice(cursor, range.start), start: cursor, end: range.start });
    }
    const effectiveStart = Math.max(range.start, cursor);
    if (range.end > effectiveStart) {
      segments.push({
        text: text.slice(effectiveStart, range.end),
        start: effectiveStart,
        end: range.end,
        highlighted: true,
      });
    }
    cursor = Math.max(cursor, range.end);
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), start: cursor, end: text.length });
  }
  return segments;
}

function applySelectionMask(
  segments: Segment[],
  selection: { start: number; end: number } | null,
): Segment[] {
  if (!selection) return segments;
  const lo = Math.min(selection.start, selection.end);
  const hi = Math.max(selection.start, selection.end);
  if (lo === hi) return segments;

  const out: Segment[] = [];
  for (const seg of segments) {
    if (!seg.highlighted || seg.end <= lo || seg.start >= hi) {
      out.push(seg);
      continue;
    }
    const overlapStart = Math.max(seg.start, lo);
    const overlapEnd = Math.min(seg.end, hi);
    if (seg.start < overlapStart) {
      out.push({
        text: seg.text.slice(0, overlapStart - seg.start),
        start: seg.start,
        end: overlapStart,
        highlighted: true,
      });
    }
    out.push({
      text: seg.text.slice(overlapStart - seg.start, overlapEnd - seg.start),
      start: overlapStart,
      end: overlapEnd,
    });
    if (overlapEnd < seg.end) {
      out.push({
        text: seg.text.slice(overlapEnd - seg.start),
        start: overlapEnd,
        end: seg.end,
        highlighted: true,
      });
    }
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
