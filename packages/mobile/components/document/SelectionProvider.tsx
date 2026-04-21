import React, {
  createContext,
  forwardRef,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { StyleSheet, View } from "react-native";
import type { SkParagraph } from "@shopify/react-native-skia";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import { scheduleOnRN } from "react-native-worklets";

const HANDLE_SIZE = 14;
const HANDLE_HIT_SLOP = 40;
const HANDLE_COLOR = "#007AFF";
const LINE_HEIGHT = 24;

export type Endpoint = { nodeId: string; offset: number };
export type Selection = { anchor: Endpoint; focus: Endpoint };

export interface NodeSlice {
  nodeId: string;
  start: number;
  end: number;
}

export interface NormalizedSelection {
  start: Endpoint;
  end: Endpoint;
  slices: NodeSlice[];
}

interface NodeEntry {
  nodeId: string;
  paragraph: SkParagraph;
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface SelectionContextValue {
  selection: Selection | null;
  orderOf: (nodeId: string) => number;
  registerNode: (entry: NodeEntry) => void;
  unregisterNode: (nodeId: string) => void;
  setSelectionForNode: (nodeId: string, start: number, end: number) => void;
  clearSelection: () => void;
  disabled: boolean;
  getRootView: () => View | null;
}

const SelectionContext = createContext<SelectionContextValue | null>(null);

export function useSelection(): SelectionContextValue {
  const ctx = useContext(SelectionContext);
  if (!ctx) throw new Error("useSelection must be used inside SelectionProvider");
  return ctx;
}

export interface SelectionProviderHandle {
  clear: () => void;
}

interface Props {
  children: ReactNode;
  disabled?: boolean;
  onSelectionChange: (sel: NormalizedSelection | null) => void;
}

export const SelectionProvider = forwardRef<SelectionProviderHandle, Props>(
  function SelectionProvider({ children, disabled = false, onSelectionChange }, ref) {
    const rootRef = useRef<View>(null);
    const registryRef = useRef<Map<string, NodeEntry>>(new Map());
    const orderMapRef = useRef<Map<string, number>>(new Map());
    const [orderVersion, setOrderVersion] = useState(0);

    const [selection, setSelectionState] = useState<Selection | null>(null);
    const selectionRef = useRef<Selection | null>(null);
    selectionRef.current = selection;

    const onSelectionChangeRef = useRef(onSelectionChange);
    onSelectionChangeRef.current = onSelectionChange;

    const recomputeOrder = useCallback(() => {
      const entries = Array.from(registryRef.current.values()).sort(
        (a, b) => a.y - b.y || a.x - b.x,
      );
      const m = new Map<string, number>();
      entries.forEach((e, i) => m.set(e.nodeId, i));
      orderMapRef.current = m;
      setOrderVersion((v) => v + 1);
    }, []);

    const registerNode = useCallback(
      (entry: NodeEntry) => {
        registryRef.current.set(entry.nodeId, entry);
        recomputeOrder();
      },
      [recomputeOrder],
    );

    const unregisterNode = useCallback(
      (nodeId: string) => {
        registryRef.current.delete(nodeId);
        recomputeOrder();
      },
      [recomputeOrder],
    );

    const orderOf = useCallback(
      (nodeId: string) => orderMapRef.current.get(nodeId) ?? -1,
      [],
    );

    const emit = useCallback((sel: Selection | null) => {
      if (!sel) {
        onSelectionChangeRef.current(null);
        return;
      }
      const norm = normalize(sel, orderMapRef.current, registryRef.current);
      onSelectionChangeRef.current(norm);
    }, []);

    const setSelectionForNode = useCallback(
      (nodeId: string, start: number, end: number) => {
        if (start === end) {
          setSelectionState(null);
          emit(null);
          return;
        }
        const sel: Selection = {
          anchor: { nodeId, offset: start },
          focus: { nodeId, offset: end },
        };
        setSelectionState(sel);
        emit(sel);
      },
      [emit],
    );

    const clearSelection = useCallback(() => {
      setSelectionState(null);
      emit(null);
    }, [emit]);

    useImperativeHandle(ref, () => ({ clear: clearSelection }), [clearSelection]);

    useEffect(() => {
      if (disabled) {
        setSelectionState(null);
        emit(null);
      }
    }, [disabled, emit]);

    const hitTestNode = useCallback((y: number): NodeEntry | null => {
      let best: NodeEntry | null = null;
      let bestDist = Infinity;
      for (const e of registryRef.current.values()) {
        if (y >= e.y && y <= e.y + e.height) return e;
        const dist = y < e.y ? e.y - y : y - (e.y + e.height);
        if (dist < bestDist) {
          bestDist = dist;
          best = e;
        }
      }
      return best;
    }, []);

    const hitTestPos = useCallback((entry: NodeEntry, x: number, y: number): number => {
      const lx = Math.max(0, Math.min(entry.width, x - entry.x));
      const ly = Math.max(0, Math.min(entry.height, y - entry.y));
      return entry.paragraph.getGlyphPositionAtCoordinate(lx, ly);
    }, []);

    const handleDragStart = useCallback(
      (x: number, y: number) => {
        const entry = hitTestNode(y);
        if (!entry) return;
        const pos = hitTestPos(entry, x, y);
        const word = wordBoundsAt(entry.text, pos);
        setSelectionState({
          anchor: { nodeId: entry.nodeId, offset: word.start },
          focus: { nodeId: entry.nodeId, offset: word.end },
        });
      },
      [hitTestNode, hitTestPos],
    );

    const handleDragUpdate = useCallback(
      (x: number, y: number) => {
        const entry = hitTestNode(y);
        if (!entry) return;
        const pos = hitTestPos(entry, x, y);
        setSelectionState((prev) => {
          if (!prev) {
            return {
              anchor: { nodeId: entry.nodeId, offset: pos },
              focus: { nodeId: entry.nodeId, offset: pos },
            };
          }
          return { ...prev, focus: { nodeId: entry.nodeId, offset: pos } };
        });
      },
      [hitTestNode, hitTestPos],
    );

    const handleDragEnd = useCallback(() => {
      emit(selectionRef.current);
    }, [emit]);

    const handleOuterTap = useCallback(
      (x: number, y: number) => {
        for (const e of registryRef.current.values()) {
          if (y >= e.y && y <= e.y + e.height && x >= e.x && x <= e.x + e.width) {
            // Tap landed on a registered node; let the node's own tap handle it.
            return;
          }
        }
        clearSelection();
      },
      [clearSelection],
    );

    const outerTap = useMemo(
      () =>
        Gesture.Tap()
          .enabled(!disabled)
          .onEnd((e, success) => {
            if (!success) return;
            scheduleOnRN(handleOuterTap, e.x, e.y);
          }),
      [disabled, handleOuterTap],
    );

    const pan = useMemo(
      () =>
        Gesture.Pan()
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
          }),
      [disabled, handleDragStart, handleDragUpdate, handleDragEnd],
    );

    const rootGesture = useMemo(
      () => Gesture.Simultaneous(pan, outerTap),
      [pan, outerTap],
    );

    const handleAnchors = useMemo(() => {
      if (!selection) return null;
      const norm = normalize(selection, orderMapRef.current, registryRef.current);
      if (!norm || norm.slices.length === 0) return null;
      const first = norm.slices[0];
      const last = norm.slices[norm.slices.length - 1];
      const firstEntry = registryRef.current.get(first.nodeId);
      const lastEntry = registryRef.current.get(last.nodeId);
      if (!firstEntry || !lastEntry) return null;
      const firstRects = firstEntry.paragraph.getRectsForRange(first.start, first.end);
      const lastRects = lastEntry.paragraph.getRectsForRange(last.start, last.end);
      if (firstRects.length === 0 || lastRects.length === 0) return null;
      const fr = firstRects[0];
      const lr = lastRects[lastRects.length - 1];
      return {
        left: { x: firstEntry.x + fr.x, y: firstEntry.y + fr.y + fr.height },
        right: {
          x: lastEntry.x + lr.x + lr.width,
          y: lastEntry.y + lr.y + lr.height,
        },
      };
      // orderVersion triggers recompute when layouts/order change
    }, [selection, orderVersion]);

    const handleAnchorRef = useRef<{
      which: "left" | "right";
      x: number;
      y: number;
    } | null>(null);

    const onHandleStart = useCallback(
      (which: "left" | "right") => {
        if (!handleAnchors) return;
        handleAnchorRef.current = { which, ...handleAnchors[which] };
      },
      [handleAnchors],
    );

    const onHandleMove = useCallback(
      (tx: number, ty: number) => {
        const a = handleAnchorRef.current;
        if (!a) return;
        const px = a.x + tx;
        const py = a.y + ty - LINE_HEIGHT / 2;
        const entry = hitTestNode(py);
        if (!entry) return;
        const pos = hitTestPos(entry, px, py);
        setSelectionState((prev) => {
          if (!prev) return prev;
          const norm = normalize(prev, orderMapRef.current, registryRef.current);
          if (!norm) return prev;
          const other = a.which === "left" ? norm.end : norm.start;
          const moved: Endpoint = { nodeId: entry.nodeId, offset: pos };
          return { anchor: other, focus: moved };
        });
      },
      [hitTestNode, hitTestPos],
    );

    const onHandleEnd = useCallback(() => {
      emit(selectionRef.current);
    }, [emit]);

    const leftHandleGesture = useMemo(
      () =>
        Gesture.Pan()
          .onStart(() => {
            scheduleOnRN(onHandleStart, "left");
          })
          .onUpdate((e) => {
            scheduleOnRN(onHandleMove, e.translationX, e.translationY);
          })
          .onEnd(() => {
            scheduleOnRN(onHandleEnd);
          }),
      [onHandleStart, onHandleMove, onHandleEnd],
    );

    const rightHandleGesture = useMemo(
      () =>
        Gesture.Pan()
          .onStart(() => {
            scheduleOnRN(onHandleStart, "right");
          })
          .onUpdate((e) => {
            scheduleOnRN(onHandleMove, e.translationX, e.translationY);
          })
          .onEnd(() => {
            scheduleOnRN(onHandleEnd);
          }),
      [onHandleStart, onHandleMove, onHandleEnd],
    );

    const getRootView = useCallback(() => rootRef.current, []);

    const contextValue = useMemo<SelectionContextValue>(
      () => ({
        selection,
        orderOf,
        registerNode,
        unregisterNode,
        setSelectionForNode,
        clearSelection,
        disabled,
        getRootView,
      }),
      [
        selection,
        orderVersion,
        orderOf,
        registerNode,
        unregisterNode,
        setSelectionForNode,
        clearSelection,
        disabled,
        getRootView,
      ],
    );

    return (
      <SelectionContext.Provider value={contextValue}>
        <View ref={rootRef} collapsable={false}>
          <GestureDetector gesture={rootGesture}>
            <View collapsable={false}>{children}</View>
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
      </SelectionContext.Provider>
    );
  },
);

function normalize(
  sel: Selection,
  orderMap: Map<string, number>,
  registry: Map<string, NodeEntry>,
): NormalizedSelection | null {
  const aOrder = orderMap.get(sel.anchor.nodeId) ?? -1;
  const fOrder = orderMap.get(sel.focus.nodeId) ?? -1;
  if (aOrder < 0 || fOrder < 0) return null;

  let start: Endpoint;
  let end: Endpoint;
  if (
    aOrder < fOrder ||
    (aOrder === fOrder && sel.anchor.offset <= sel.focus.offset)
  ) {
    start = sel.anchor;
    end = sel.focus;
  } else {
    start = sel.focus;
    end = sel.anchor;
  }

  if (start.nodeId === end.nodeId && start.offset === end.offset) return null;

  const sOrder = orderMap.get(start.nodeId)!;
  const eOrder = orderMap.get(end.nodeId)!;
  const ordered = Array.from(registry.values()).sort(
    (a, b) => (orderMap.get(a.nodeId) ?? 0) - (orderMap.get(b.nodeId) ?? 0),
  );

  const slices: NodeSlice[] = [];
  for (const entry of ordered) {
    const o = orderMap.get(entry.nodeId)!;
    if (o < sOrder || o > eOrder) continue;
    let s = 0;
    let e = entry.text.length;
    if (o === sOrder) s = start.offset;
    if (o === eOrder) e = end.offset;
    if (s < e) slices.push({ nodeId: entry.nodeId, start: s, end: e });
  }

  return { start, end, slices };
}

export function wordBoundsAt(
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
  handle: {
    position: "absolute",
    width: HANDLE_SIZE,
    height: HANDLE_SIZE,
    borderRadius: HANDLE_SIZE / 2,
    backgroundColor: HANDLE_COLOR,
  },
});
