import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LayoutChangeEvent, StyleSheet, View } from "react-native";
import {
  Canvas,
  FontStyle,
  Paragraph,
  Rect,
  Skia,
  SkParagraph,
  TextAlign,
} from "@shopify/react-native-skia";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import { scheduleOnRN } from "react-native-worklets";
import type { HighlightRead } from "@precis/shared";
import { useSelection, useSelectionSlice, wordBoundsAt } from "./SelectionProvider";

const HIGHLIGHT_YELLOW = "#FFF176";
const SELECTION_BLUE = "rgba(0, 122, 255, 0.35)";
const DEFAULT_FONT_SIZE = 15;
const DEFAULT_LINE_HEIGHT = 24;
const TEXT_COLOR = "#1a1a1a";

interface HighlightableTextProps {
  nodeId: string;
  text: string;
  highlights: HighlightRead[];
  fontSize?: number;
  lineHeight?: number;
  bold?: boolean;
}

export function HighlightableText({
  nodeId,
  text,
  highlights,
  fontSize = DEFAULT_FONT_SIZE,
  lineHeight,
  bold = false,
}: HighlightableTextProps) {
  const resolvedLineHeight = lineHeight ?? Math.round(fontSize * (DEFAULT_LINE_HEIGHT / DEFAULT_FONT_SIZE));
  const {
    registerNode,
    unregisterNode,
    setSelectionForNode,
    clearSelection,
    disabled,
    getRootView,
  } = useSelection();

  const [width, setWidth] = useState(0);
  const viewRef = useRef<View>(null);

  const paragraph = useMemo<SkParagraph | null>(() => {
    if (!width) return null;
    const style = { textAlign: TextAlign.Left };
    const textStyle = {
      color: Skia.Color(TEXT_COLOR),
      fontSize,
      heightMultiplier: resolvedLineHeight / fontSize,
      fontStyle: bold ? FontStyle.Bold : FontStyle.Normal,
    };
    const builder = Skia.ParagraphBuilder.Make(style);
    builder.pushStyle(textStyle);
    builder.addText(text);
    builder.pop();
    const p = builder.build();
    p.layout(width);
    return p;
  }, [text, width, fontSize, resolvedLineHeight, bold]);

  const height = paragraph ? paragraph.getHeight() : resolvedLineHeight;

  const measureAndRegister = useCallback(() => {
    const root = getRootView();
    const node = viewRef.current;
    if (!root || !node || !paragraph) return;
    node.measureLayout(
      root,
      (x: number, y: number, w: number, h: number) => {
        registerNode({ nodeId, paragraph, text, x, y, width: w, height: h });
      },
      () => {
        /* ignore measurement errors */
      },
    );
  }, [getRootView, nodeId, paragraph, registerNode, text]);

  useEffect(() => {
    measureAndRegister();
    return () => unregisterNode(nodeId);
  }, [measureAndRegister, nodeId, unregisterNode]);

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

  const slice = useSelectionSlice(nodeId, text.length);

  const selectionRects = useMemo(() => {
    if (!paragraph || !slice) return [];
    return paragraph.getRectsForRange(slice.start, slice.end);
  }, [paragraph, slice]);

  const findHighlightAt = useCallback(
    (pos: number) =>
      highlights.find(
        (h) =>
          h.start_offset != null &&
          h.end_offset != null &&
          pos >= h.start_offset &&
          pos <= h.end_offset,
      ),
    [highlights],
  );

  const handleTap = useCallback(
    (x: number, y: number) => {
      if (!paragraph) return;
      const pos = paragraph.getGlyphPositionAtCoordinate(x, y);
      const hit = findHighlightAt(pos);
      if (hit && hit.start_offset != null && hit.end_offset != null) {
        setSelectionForNode(nodeId, hit.start_offset, hit.end_offset);
        return;
      }
      const word = wordBoundsAt(text, pos);
      if (word.start !== word.end) {
        setSelectionForNode(nodeId, word.start, word.end);
      } else {
        clearSelection();
      }
    },
    [paragraph, findHighlightAt, setSelectionForNode, clearSelection, text, nodeId],
  );

  const tap = useMemo(
    () =>
      Gesture.Tap()
        .enabled(!disabled)
        .onEnd((e) => {
          scheduleOnRN(handleTap, e.x, e.y);
        }),
    [disabled, handleTap],
  );

  const onLayout = (e: LayoutChangeEvent) => {
    const w = e.nativeEvent.layout.width;
    if (w && w !== width) setWidth(w);
    measureAndRegister();
  };

  return (
    <View ref={viewRef} style={styles.wrapper} onLayout={onLayout} collapsable={false}>
      <GestureDetector gesture={tap}>
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
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    width: "100%",
  },
});
