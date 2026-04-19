import React, { useMemo, useState, useCallback, useEffect } from "react";
import { View, StyleSheet, LayoutChangeEvent } from "react-native";
import {
  Canvas,
  Paragraph,
  Rect,
  Skia,
  TextAlign,
  FontStyle,
  SkParagraph,
} from "@shopify/react-native-skia";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import { scheduleOnRN } from "react-native-worklets";
import type { HighlightRead } from "@precis/shared";

const HIGHLIGHT_YELLOW = "#FFF176";
const SELECTION_BLUE = "rgba(0, 122, 255, 0.35)";
const HANDLE_COLOR = "#007AFF";
const HANDLE_SIZE = 14;
const HANDLE_HIT_SLOP = 40;
const FONT_SIZE = 15;
const LINE_HEIGHT = 24;
const TEXT_COLOR = "#1a1a1a";

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
  disabled?: boolean;
  // The id of the node that currently owns the one allowed selection.
  // If this doesn't match `nodeId`, this component drops its local selection.
  activeSelectionNodeId?: string | null;
}

export function HighlightableText({
  nodeId,
  text,
  highlights,
  onSelectionChange,
  disabled = false,
  activeSelectionNodeId = null,
}: HighlightableTextProps) {
  const [width, setWidth] = useState(0);
  const [selection, setSelection] = useState<{
    start: number;
    end: number;
  } | null>(null);

  useEffect(() => {
    if (disabled) setSelection(null);
  }, [disabled]);

  // Enforce single-selection across all nodes: if another node becomes the
  // active selection owner, drop ours.
  useEffect(() => {
    if (activeSelectionNodeId != null && activeSelectionNodeId !== nodeId) {
      setSelection(null);
    }
  }, [activeSelectionNodeId, nodeId]);

  const paragraph = useMemo<SkParagraph | null>(() => {
    if (!width) return null;
    const style = {
      textAlign: TextAlign.Left,
    };
    const textStyle = {
      color: Skia.Color(TEXT_COLOR),
      fontSize: FONT_SIZE,
      heightMultiplier: LINE_HEIGHT / FONT_SIZE,
      fontStyle: FontStyle.Normal,
    };
    const builder = Skia.ParagraphBuilder.Make(style);
    builder.pushStyle(textStyle);
    builder.addText(text);
    builder.pop();
    const p = builder.build();
    p.layout(width);
    return p;
  }, [text, width]);

  const height = paragraph ? paragraph.getHeight() : LINE_HEIGHT;

  const highlightRects = useMemo(() => {
    if (!paragraph) return [];
    const rects: { x: number; y: number; width: number; height: number }[] = [];
    for (const h of highlights) {
      if (h.start_offset == null || h.end_offset == null) continue;
      const rs = paragraph.getRectsForRange(h.start_offset, h.end_offset);
      for (const r of rs) rects.push(r);
    }
    return rects;
  }, [paragraph, highlights]);

  const selectionRects = useMemo(() => {
    if (!paragraph || !selection) return [];
    const lo = Math.min(selection.start, selection.end);
    const hi = Math.max(selection.start, selection.end);
    if (lo === hi) return [];
    return paragraph.getRectsForRange(lo, hi);
  }, [paragraph, selection]);

  const hitTest = useCallback(
    (x: number, y: number): number => {
      if (!paragraph) return 0;
      return paragraph.getGlyphPositionAtCoordinate(x, y);
    },
    [paragraph],
  );

  const emit = useCallback(
    (start: number, end: number) => {
      const lo = Math.min(start, end);
      const hi = Math.max(start, end);
      onSelectionChange({ nodeId, start: lo, end: hi });
    },
    [nodeId, onSelectionChange],
  );

  const findHighlightAt = useCallback(
    (pos: number) => {
      return highlights.find(
        (h) =>
          h.start_offset != null &&
          h.end_offset != null &&
          pos >= h.start_offset &&
          pos <= h.end_offset,
      );
    },
    [highlights],
  );

  const handleTap = useCallback(
    (x: number, y: number) => {
      const pos = hitTest(x, y);
      const hit = findHighlightAt(pos);
      if (hit && hit.start_offset != null && hit.end_offset != null) {
        setSelection({ start: hit.start_offset, end: hit.end_offset });
        emit(hit.start_offset, hit.end_offset);
        return;
      }
      const word = wordBoundsAt(text, pos);
      if (word.start !== word.end) {
        setSelection(word);
        emit(word.start, word.end);
      } else {
        setSelection(null);
        emit(pos, pos);
      }
    },
    [hitTest, findHighlightAt, emit, text],
  );

  const handleDragStart = useCallback(
    (x: number, y: number) => {
      const pos = hitTest(x, y);
      const word = wordBoundsAt(text, pos);
      setSelection(word);
    },
    [hitTest, text],
  );

  const handleDragUpdate = useCallback(
    (x: number, y: number) => {
      const pos = hitTest(x, y);
      setSelection((prev) => {
        if (!prev) return { start: pos, end: pos };
        const anchor = pos >= prev.end ? prev.start : prev.end;
        return { start: anchor, end: pos };
      });
    },
    [hitTest],
  );

  const selectionRef = React.useRef<{ start: number; end: number } | null>(
    null,
  );
  selectionRef.current = selection;

  const handleDragEnd = useCallback(() => {
    const sel = selectionRef.current;
    if (sel) emit(sel.start, sel.end);
  }, [emit]);

  const handleAnchors = useMemo(() => {
    if (selectionRects.length === 0) return null;
    const first = selectionRects[0];
    const last = selectionRects[selectionRects.length - 1];
    return {
      left: { x: first.x, y: first.y + first.height },
      right: { x: last.x + last.width, y: last.y + last.height },
    };
  }, [selectionRects]);

  const handleAnchorRef = React.useRef<{ x: number; y: number } | null>(null);

  const handleStartLeft = useCallback(() => {
    handleAnchorRef.current = handleAnchors?.left ?? null;
  }, [handleAnchors]);

  const handleStartRight = useCallback(() => {
    handleAnchorRef.current = handleAnchors?.right ?? null;
  }, [handleAnchors]);

  const handleMove = useCallback(
    (which: "left" | "right", tx: number, ty: number) => {
      const anchor = handleAnchorRef.current;
      if (!anchor) return;
      const px = anchor.x + tx;
      const py = anchor.y + ty - LINE_HEIGHT / 2;
      const pos = hitTest(px, py);
      setSelection((prev) => {
        if (!prev) return prev;
        if (which === "left") {
          return pos < prev.end
            ? { start: pos, end: prev.end }
            : { start: prev.end, end: pos };
        }
        return pos > prev.start
          ? { start: prev.start, end: pos }
          : { start: pos, end: prev.start };
      });
    },
    [hitTest],
  );

  const handleEnd = useCallback(() => {
    const sel = selectionRef.current;
    if (sel) emit(sel.start, sel.end);
  }, [emit]);

  const leftHandleGesture = Gesture.Pan()
    .onStart(() => {
      scheduleOnRN(handleStartLeft);
    })
    .onUpdate((e) => {
      scheduleOnRN(handleMove, "left", e.translationX, e.translationY);
    })
    .onEnd(() => {
      scheduleOnRN(handleEnd);
    });

  const rightHandleGesture = Gesture.Pan()
    .onStart(() => {
      scheduleOnRN(handleStartRight);
    })
    .onUpdate((e) => {
      scheduleOnRN(handleMove, "right", e.translationX, e.translationY);
    })
    .onEnd(() => {
      scheduleOnRN(handleEnd);
    });

  const tap = Gesture.Tap()
    .enabled(!disabled)
    .onEnd((e) => {
      scheduleOnRN(handleTap, e.x, e.y);
    });

  const pan = Gesture.Pan()
    .enabled(!disabled)
    .activateAfterLongPress(250)
    .onStart((e) => {
      scheduleOnRN(handleDragStart, e.x, e.y);
    })
    .onUpdate((e) => {
      scheduleOnRN(handleDragUpdate, e.x, e.y);
    })
    .onEnd(() => {
      scheduleOnRN(handleDragEnd);
    });

  const gesture = Gesture.Exclusive(pan, tap);

  const onLayout = (e: LayoutChangeEvent) => {
    const w = e.nativeEvent.layout.width;
    if (w && w !== width) setWidth(w);
  };

  return (
    <View style={styles.wrapper} onLayout={onLayout}>
      <GestureDetector gesture={gesture}>
        <Canvas style={{ width: "100%", height }}>
          {highlightRects.map((r, i) => (
            <Rect
              key={`h-${i}`}
              x={r.x}
              y={r.y}
              width={r.width}
              height={r.height}
              color={HIGHLIGHT_YELLOW}
            />
          ))}
          {selectionRects.map((r, i) => (
            <Rect
              key={`s-${i}`}
              x={r.x}
              y={r.y}
              width={r.width}
              height={r.height}
              color={SELECTION_BLUE}
            />
          ))}
          {paragraph && (
            <Paragraph paragraph={paragraph} x={0} y={0} width={width} />
          )}
        </Canvas>
      </GestureDetector>
      {handleAnchors && !disabled && (
        <>
          <GestureDetector gesture={leftHandleGesture}>
            <View
              hitSlop={HANDLE_HIT_SLOP}
              style={[
                styles.handle,
                {
                  left: handleAnchors.left.x - HANDLE_SIZE / 2,
                  top: handleAnchors.left.y - HANDLE_SIZE / 2,
                },
              ]}
            />
          </GestureDetector>
          <GestureDetector gesture={rightHandleGesture}>
            <View
              hitSlop={HANDLE_HIT_SLOP}
              style={[
                styles.handle,
                {
                  left: handleAnchors.right.x - HANDLE_SIZE / 2,
                  top: handleAnchors.right.y - HANDLE_SIZE / 2,
                },
              ]}
            />
          </GestureDetector>
        </>
      )}
    </View>
  );
}

function wordBoundsAt(
  text: string,
  pos: number,
): { start: number; end: number } {
  const isWord = (c: string) => /\S/.test(c);
  const n = text.length;
  if (n === 0) return { start: 0, end: 0 };
  let p = Math.max(0, Math.min(n, pos));
  if (p === n || !isWord(text[p])) {
    if (p > 0 && isWord(text[p - 1])) p = p - 1;
    else return { start: p, end: p };
  }
  let start = p;
  while (start > 0 && isWord(text[start - 1])) start--;
  let end = p;
  while (end < n && isWord(text[end])) end++;
  return { start, end };
}

const styles = StyleSheet.create({
  wrapper: {
    width: "100%",
  },
  handle: {
    position: "absolute",
    width: HANDLE_SIZE,
    height: HANDLE_SIZE,
    borderRadius: HANDLE_SIZE / 2,
    backgroundColor: HANDLE_COLOR,
  },
});
