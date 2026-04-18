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
import type { TextSelection } from "../../../components/document/HighlightableText";
import type { HighlightCreate, HighlightRead } from "@precis/shared";

const FLUSH_DEBOUNCE_MS = 500;
const TEMP_ID_PREFIX = "temp_";

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

  const [selection, setSelection] = useState<TextSelection | null>(null);

  const handleSelectionChange = useCallback((sel: TextSelection) => {
    if (sel.start === sel.end) {
      setSelection((prev) => (prev && prev.nodeId === sel.nodeId ? null : prev));
    } else {
      setSelection(sel);
    }
  }, []);

  const overlapping = useMemo(() => {
    if (!selection) return [];
    return highlights.filter(
      (h) =>
        h.node_id === selection.nodeId &&
        h.start_offset != null &&
        h.end_offset != null &&
        h.start_offset < selection.end &&
        h.end_offset > selection.start,
    );
  }, [selection, highlights]);

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
    (sel: TextSelection) => {
      const tempId = `${TEMP_ID_PREFIX}${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
      const now = new Date().toISOString();
      const optimistic: HighlightRead = {
        id: tempId,
        document_id: id,
        node_id: sel.nodeId,
        start_offset: sel.start,
        end_offset: sel.end,
        created_at: now,
        updated_at: now,
      };
      pendingAddsRef.current.push({
        create: { node_id: sel.nodeId, start_offset: sel.start, end_offset: sel.end },
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

  const handleFabPress = () => {
    if (!selection) return;
    if (overlapping.length > 0) {
      removeHighlightsByIds(overlapping.map((h) => h.id));
    } else {
      addHighlight(selection);
    }
    setSelection(null);
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
  const fabLabel = overlapping.length > 0 ? "Remove highlight" : "Add highlight";

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
          onPress={() => router.push(`/(app)/documents/${id}/settings`)}
        >
          <Text style={styles.toolBtnText}>Settings</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        <NodeRenderer
          nodes={nodes}
          highlights={highlights}
          onSelectionChange={handleSelectionChange}
        />
      </ScrollView>

      {fabVisible && (
        <TouchableOpacity
          activeOpacity={0.85}
          style={styles.fab}
          onPress={handleFabPress}
        >
          <Text style={styles.fabText}>{fabLabel}</Text>
        </TouchableOpacity>
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
  fab: {
    position: "absolute",
    left: 20,
    right: 20,
    bottom: 24,
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
  fabText: { color: "#fff", fontSize: 15, fontWeight: "600" },
});
