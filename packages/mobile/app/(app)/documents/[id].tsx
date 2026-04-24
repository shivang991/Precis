import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  View,
  ScrollView,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "../../../hooks/useApi";
import { NodeRenderer } from "../../../components/document/NodeRenderer";
import {
  SelectionProvider,
  SelectionProviderHandle,
  NormalizedSelection,
  NodeSlice,
} from "../../../components/document/SelectionProvider";
import type { HighlightCreate, HighlightRead } from "@precis/shared";

const FLUSH_DEBOUNCE_MS = 500;
const TEMP_ID_PREFIX = "temp_";

type Remainder = { nodeId: string; start: number; end: number };

export default function DocumentViewerScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const api = useApi();
  const qc = useQueryClient();

  const { data: document, isLoading: docLoading } = useQuery({
    queryKey: ["document", id],
    queryFn: () => api.getDocument(id),
    enabled: !!id,
  });

  const { data: highlights = [] } = useQuery({
    queryKey: ["highlights", id],
    queryFn: () => api.listHighlights(id),
    enabled: !!id && document?.status === "ready",
  });

  const [selection, setSelection] = useState<NormalizedSelection | null>(null);
  const [highlighterOn, setHighlighterOn] = useState(true);
  const selectionProviderRef = useRef<SelectionProviderHandle>(null);

  const handleSelectionChange = useCallback((sel: NormalizedSelection | null) => {
    setSelection(sel);
  }, []);

  // Per-slice overlap with existing highlights.
  const overlappingByNode = useMemo(() => {
    if (!selection) return [] as Array<{ slice: NodeSlice; overs: HighlightRead[] }>;
    return selection.slices.map((slice) => ({
      slice,
      overs: highlights.filter(
        (h) =>
          h.node_id === slice.nodeId &&
          h.start_offset != null &&
          h.end_offset != null &&
          h.start_offset < slice.end &&
          h.end_offset > slice.start,
      ),
    }));
  }, [selection, highlights]);

  // Aggregate coverage over all slices:
  //   "none"    → no slice has any overlap
  //   "full"    → every slice is fully covered
  //   "partial" → some overlap but at least one gap
  const coverage: "none" | "full" | "partial" = useMemo(() => {
    if (!selection || overlappingByNode.length === 0) return "none";
    let anyOverlap = false;
    let anyGap = false;
    for (const { slice, overs } of overlappingByNode) {
      if (overs.length === 0) {
        anyGap = true;
        continue;
      }
      anyOverlap = true;
      const clipped = overs
        .map((h) => ({
          start: Math.max(h.start_offset!, slice.start),
          end: Math.min(h.end_offset!, slice.end),
        }))
        .sort((a, b) => a.start - b.start);
      let cursor = slice.start;
      for (const r of clipped) {
        if (r.start > cursor) {
          anyGap = true;
          break;
        }
        if (r.end > cursor) cursor = r.end;
      }
      if (cursor < slice.end) anyGap = true;
    }
    if (!anyOverlap) return "none";
    if (!anyGap) return "full";
    return "partial";
  }, [selection, overlappingByNode]);

  const pendingAddsRef = useRef<Array<{ create: HighlightCreate; tempId: string }>>([]);
  const pendingRemovalsRef = useRef<string[]>([]);
  const flushTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flush = useCallback(async () => {
    if (flushTimer.current) {
      clearTimeout(flushTimer.current);
      flushTimer.current = null;
    }
    const adds = pendingAddsRef.current;
    const removals = pendingRemovalsRef.current;
    if (adds.length === 0 && removals.length === 0) return;
    pendingAddsRef.current = [];
    pendingRemovalsRef.current = [];
    try {
      const tasks: Promise<unknown>[] = [];
      if (adds.length) tasks.push(api.addHighlights(id, adds.map((a) => a.create)));
      if (removals.length) tasks.push(api.removeHighlights(id, removals));
      await Promise.all(tasks);
      qc.invalidateQueries({ queryKey: ["highlights", id] });
    } catch (e: any) {
      qc.invalidateQueries({ queryKey: ["highlights", id] });
      Alert.alert("Highlight sync failed", e?.message ?? "Unknown error");
    }
  }, [api, id, qc]);

  const flushRef = useRef(flush);
  flushRef.current = flush;

  const scheduleFlush = useCallback(() => {
    if (flushTimer.current) clearTimeout(flushTimer.current);
    flushTimer.current = setTimeout(() => {
      void flushRef.current();
    }, FLUSH_DEBOUNCE_MS);
  }, []);

  useEffect(() => {
    return () => {
      if (flushTimer.current) clearTimeout(flushTimer.current);
      void flushRef.current();
    };
  }, []);

  const addHighlight = useCallback(
    (r: { nodeId: string; start: number; end: number }) => {
      const tempId = `${TEMP_ID_PREFIX}${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
      const now = new Date().toISOString();
      const optimistic: HighlightRead = {
        id: tempId,
        document_id: id,
        node_id: r.nodeId,
        start_offset: r.start,
        end_offset: r.end,
        created_at: now,
        updated_at: now,
      };
      pendingAddsRef.current.push({
        create: { node_id: r.nodeId, start_offset: r.start, end_offset: r.end },
        tempId,
      });
      qc.setQueryData<HighlightRead[]>(["highlights", id], (prev = []) => [...prev, optimistic]);
      scheduleFlush();
    },
    [id, qc, scheduleFlush],
  );

  const removeHighlightsByIds = useCallback(
    (ids: string[]) => {
      if (ids.length === 0) return;
      for (const hid of ids) {
        if (hid.startsWith(TEMP_ID_PREFIX)) {
          const idx = pendingAddsRef.current.findIndex((a) => a.tempId === hid);
          if (idx >= 0) pendingAddsRef.current.splice(idx, 1);
        } else {
          pendingRemovalsRef.current.push(hid);
        }
      }
      const idSet = new Set(ids);
      qc.setQueryData<HighlightRead[]>(["highlights", id], (prev = []) =>
        prev.filter((h) => !idSet.has(h.id)),
      );
      scheduleFlush();
    },
    [id, qc, scheduleFlush],
  );

  const clearUiSelection = () => {
    selectionProviderRef.current?.clear();
    setSelection(null);
  };

  const handleAddPress = () => {
    if (!selection) return;
    for (const slice of selection.slices) {
      addHighlight({ nodeId: slice.nodeId, start: slice.start, end: slice.end });
    }
    clearUiSelection();
  };

  const handleRemovePress = () => {
    if (!selection) return;
    // For each slice, drop overlapping highlights and re-add the parts that
    // stick out beyond the slice so only the intersecting portion is erased.
    const remainders: Remainder[] = [];
    const idsToRemove: string[] = [];
    for (const { slice, overs } of overlappingByNode) {
      for (const h of overs) {
        if (h.start_offset == null || h.end_offset == null) continue;
        idsToRemove.push(h.id);
        if (h.start_offset < slice.start) {
          remainders.push({ nodeId: slice.nodeId, start: h.start_offset, end: slice.start });
        }
        if (h.end_offset > slice.end) {
          remainders.push({ nodeId: slice.nodeId, start: slice.end, end: h.end_offset });
        }
      }
    }
    removeHighlightsByIds(idsToRemove);
    for (const r of remainders) addHighlight(r);
    clearUiSelection();
  };

  if (docLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!document) {
    return (
      <View style={styles.center}>
        <Text>Document not found.</Text>
      </View>
    );
  }

  if (document.status !== "ready") {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text style={styles.processingText}>Processing document…</Text>
      </View>
    );
  }

  const nodes = document.document_content_tree?.nodes ?? [];
  const fabVisible = selection != null;
  const showAdd = coverage !== "full";
  const showRemove = coverage !== "none";

  return (
    <View style={styles.container}>
      <View style={styles.toolbar}>
        <TouchableOpacity
          style={styles.toolBtn}
          onPress={() => router.push(`/(app)/documents/${id}/summary`)}
        >
          <Text style={styles.toolBtnText}>Summary</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.toolBtn}
          onPress={() => {
            setHighlighterOn((v) => !v);
          }}
        >
          <Text style={styles.toolBtnText}>Highlighter: {highlighterOn ? "On" : "Off"}</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        <SelectionProvider
          ref={selectionProviderRef}
          disabled={!highlighterOn}
          onSelectionChange={handleSelectionChange}
        >
          <NodeRenderer nodes={nodes} highlights={highlights} />
        </SelectionProvider>
      </ScrollView>

      {fabVisible && (
        <View style={styles.fabRow}>
          {showRemove && (
            <TouchableOpacity
              activeOpacity={0.85}
              style={[styles.fab, styles.fabFlex]}
              onPress={handleRemovePress}
            >
              <Text style={styles.fabText}>Remove highlight</Text>
            </TouchableOpacity>
          )}
          {showAdd && (
            <TouchableOpacity
              activeOpacity={0.85}
              style={[styles.fab, styles.fabFlex]}
              onPress={handleAddPress}
            >
              <Text style={styles.fabText}>Add highlight</Text>
            </TouchableOpacity>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  processingText: { marginTop: 12, color: "#666" },
  toolbar: {
    flexDirection: "row",
    alignItems: "center",
    padding: 8,
    gap: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#e0e0e0",
    flexWrap: "wrap",
  },
  toolBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#ccc",
  },
  toolBtnText: { fontSize: 13, color: "#333" },
  scroll: { flex: 1 },
  content: { padding: 16, paddingBottom: 96 },
  fabRow: {
    position: "absolute",
    left: 20,
    right: 20,
    bottom: 24,
    flexDirection: "row",
    gap: 12,
  },
  fab: {
    backgroundColor: "#1a1a1a",
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  fabFlex: { flex: 1 },
  fabText: { color: "#fff", fontSize: 15, fontWeight: "600" },
});
