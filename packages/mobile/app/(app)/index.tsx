import { useState } from 'react';

import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';

import * as DocumentPicker from 'expo-document-picker';
import { useRouter } from 'expo-router';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import type { DocumentRead } from '@precis/shared';

import { API_BASE_URL } from '../../constants/api';
import { useApi } from '../../hooks/useApi';
import { useAuthStore } from '../../store/auth';

type DocumentSource = 'digital' | 'scanned';

export default function FilesListScreen() {
  const router = useRouter();
  const api = useApi();
  const qc = useQueryClient();
  const token = useAuthStore((s) => s.token);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => api.listDocuments(),
  });

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => api.deleteDocument(documentId),
    onMutate: async (documentId: string) => {
      await qc.cancelQueries({ queryKey: ['documents'] });
      const previous = qc.getQueryData<DocumentRead[]>(['documents']);
      qc.setQueryData<DocumentRead[]>(['documents'], (old) =>
        old ? old.filter((d) => d.id !== documentId) : old,
      );
      return { previous };
    },
    onError: (e: unknown, _id, ctx) => {
      if (ctx?.previous) qc.setQueryData(['documents'], ctx.previous);
      Alert.alert('Delete failed', e instanceof Error ? e.message : 'Unknown error');
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const confirmDelete = (doc: DocumentRead) => {
    Alert.alert('Delete document', `Delete "${doc.title}"?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: () => deleteMutation.mutate(doc.id),
      },
    ]);
  };

  const uploadMutation = useMutation({
    mutationFn: async (source: DocumentSource) => {
      const result = await DocumentPicker.getDocumentAsync({
        type: 'application/pdf',
        copyToCacheDirectory: true,
      });
      if (result.canceled) return;

      const asset = result.assets[0];
      const file = {
        uri: asset.uri,
        name: asset.name,
        type: asset.mimeType ?? 'application/pdf',
      } as unknown as Blob;
      const doc = await api.uploadDocument(
        { file, source },
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );
      return doc;
    },
    onSuccess: async (doc) => {
      if (!doc) return;
      qc.invalidateQueries({ queryKey: ['documents'] });

      // Kick off processing via SSE
      setProcessingId(doc.id);
      try {
        const res = await fetch(`${API_BASE_URL}/api/v1/documents/${doc.id}/process`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Process failed (${res.status})`);

        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            if (chunk.includes('error')) {
              throw new Error('Processing failed on server');
            }
          }
        }

        qc.invalidateQueries({ queryKey: ['documents'] });
        router.push(`/(app)/documents/${doc.id}`);
      } catch (e: unknown) {
        Alert.alert('Processing failed', e instanceof Error ? e.message : 'Unknown error');
      } finally {
        setProcessingId(null);
      }
    },
    onError: (e: unknown) =>
      Alert.alert('Upload failed', e instanceof Error ? e.message : 'Unknown error'),
  });

  const isBusy = uploadMutation.isPending || processingId !== null;

  const renderItem = ({ item }: { item: DocumentRead }) => {
    const isDeleting = deleteMutation.isPending && deleteMutation.variables === item.id;
    return (
      <View style={styles.row}>
        <Text style={styles.docTitle} numberOfLines={1}>
          {item.title}
        </Text>
        <Text style={styles.docMeta}>
          {item.source} · {item.status}
        </Text>
        <View style={styles.actions}>
          <TouchableOpacity
            style={styles.openBtn}
            onPress={() => router.push(`/(app)/documents/${item.id}`)}
          >
            <Text style={styles.openBtnText}>Open</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.deleteBtn, isDeleting && styles.deleteBtnDisabled]}
            onPress={() => confirmDelete(item)}
            disabled={isDeleting}
          >
            <Text style={styles.deleteBtnText}>{isDeleting ? 'Deleting…' : 'Delete'}</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.heading}>Your Files</Text>
        <TouchableOpacity style={styles.settingsBtn} onPress={() => router.push('/(app)/settings')}>
          <Text style={styles.settingsBtnText}>Settings</Text>
        </TouchableOpacity>
      </View>

      {isBusy && (
        <View style={styles.processingBanner}>
          <ActivityIndicator color="#fff" size="small" />
          <Text style={styles.processingText}>
            {uploadMutation.isPending ? 'Uploading…' : 'Processing…'}
          </Text>
        </View>
      )}

      {isLoading ? (
        <ActivityIndicator style={{ marginTop: 48 }} />
      ) : (
        <FlatList
          data={documents}
          keyExtractor={(d) => d.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <Text style={styles.empty}>No documents yet. Upload a PDF below.</Text>
          }
        />
      )}

      <View style={styles.uploadBar}>
        <TouchableOpacity
          style={[styles.uploadBtn, isBusy && styles.uploadBtnDisabled]}
          onPress={() => uploadMutation.mutate('digital')}
          disabled={isBusy}
        >
          <Text style={styles.uploadBtnText}>Upload Digital PDF</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.uploadBtn, isBusy && styles.uploadBtnDisabled]}
          onPress={() => uploadMutation.mutate('scanned')}
          disabled={isBusy}
        >
          <Text style={styles.uploadBtnText}>Upload Scanned PDF</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#e0e0e0',
  },
  heading: { fontSize: 22, fontWeight: '700' },
  settingsBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
  },
  settingsBtnText: { fontSize: 13, color: '#333' },
  processingBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#1a1a1a',
    paddingVertical: 10,
  },
  processingText: { color: '#fff', fontSize: 13 },
  list: { padding: 16, gap: 2 },
  row: {
    flexDirection: 'column',
    alignItems: 'stretch',
    paddingVertical: 14,
    gap: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#e0e0e0',
  },
  docTitle: { fontSize: 15, fontWeight: '500' },
  docMeta: { fontSize: 12, color: '#888', marginTop: 2 },
  actions: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 6,
  },
  openBtn: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#1a73e8',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  openBtnText: { fontSize: 14, color: '#1a73e8', fontWeight: '500' },
  deleteBtn: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#d93025',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  deleteBtnDisabled: { opacity: 0.5 },
  deleteBtnText: { fontSize: 14, color: '#d93025', fontWeight: '500' },
  empty: { textAlign: 'center', color: '#999', marginTop: 48 },
  uploadBar: {
    flexDirection: 'row',
    gap: 12,
    padding: 16,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#e0e0e0',
  },
  uploadBtn: {
    flex: 1,
    backgroundColor: '#1a1a1a',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  uploadBtnDisabled: { opacity: 0.5 },
  uploadBtnText: { color: '#fff', fontSize: 14, fontWeight: '600' },
});
