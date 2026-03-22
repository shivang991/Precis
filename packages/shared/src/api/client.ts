import axios, { type AxiosInstance } from "axios";
import type { User, UserSettingsUpdate } from "../types/user";
import type { Document, DocumentSettingsUpdate, DocumentContentPatch } from "../types/document";
import type { Highlight, HighlightCreate, HighlightUpdate, SummarySection } from "../types/highlight";

export function createApiClient(baseURL: string, getToken: () => string | null): ApiClient {
  const http: AxiosInstance = axios.create({ baseURL });

  http.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  return {
    // Auth
    getLoginUrl: () =>
      http.get<{ url: string }>("/api/v1/auth/login").then((r) => r.data),
    getLoginUrlForMobile: (redirectUri: string) =>
      http
        .get<{ url: string }>("/api/v1/auth/login", { params: { redirect_uri: redirectUri } })
        .then((r) => r.data),
    exchangeCode: (code: string, redirectUri?: string) =>
      http
        .post<{ access_token: string; token_type: string }>("/api/v1/auth/token", {
          code,
          redirect_uri: redirectUri,
        })
        .then((r) => r.data),
    getMe: () => http.get<User>("/api/v1/auth/me").then((r) => r.data),

    // Users
    getProfile: () => http.get<User>("/api/v1/users/me").then((r) => r.data),
    updateSettings: (data: UserSettingsUpdate) =>
      http.patch<User>("/api/v1/users/me/settings", data).then((r) => r.data),

    // Documents
    listDocuments: () =>
      http.get<Document[]>("/api/v1/documents").then((r) => r.data),
    getDocument: (id: string) =>
      http.get<Document>(`/api/v1/documents/${id}`).then((r) => r.data),
    uploadDocument: (file: FormData) =>
      http.post<Document>("/api/v1/documents/upload", file, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then((r) => r.data),
    updateDocumentSettings: (id: string, data: DocumentSettingsUpdate) =>
      http.patch<Document>(`/api/v1/documents/${id}/settings`, data).then((r) => r.data),
    patchDocumentContent: (id: string, patch: DocumentContentPatch) =>
      http.patch<Document>(`/api/v1/documents/${id}/content`, patch).then((r) => r.data),
    deleteDocument: (id: string) =>
      http.delete(`/api/v1/documents/${id}`).then((r) => r.data),

    // Highlights
    listHighlights: (documentId: string) =>
      http.get<Highlight[]>(`/api/v1/documents/${documentId}/highlights`).then((r) => r.data),
    createHighlight: (documentId: string, data: HighlightCreate) =>
      http.post<Highlight>(`/api/v1/documents/${documentId}/highlights`, data).then((r) => r.data),
    updateHighlight: (documentId: string, highlightId: string, data: HighlightUpdate) =>
      http
        .patch<Highlight>(`/api/v1/documents/${documentId}/highlights/${highlightId}`, data)
        .then((r) => r.data),
    deleteHighlight: (documentId: string, highlightId: string) =>
      http.delete(`/api/v1/documents/${documentId}/highlights/${highlightId}`).then((r) => r.data),
    clearHighlights: (documentId: string) =>
      http.delete(`/api/v1/documents/${documentId}/highlights`).then((r) => r.data),
    getSummary: (documentId: string) =>
      http
        .get<SummarySection[]>(`/api/v1/documents/${documentId}/highlights/summary`)
        .then((r) => r.data),

    // Export
    exportDocumentPdf: (documentId: string) =>
      http
        .get(`/api/v1/export/documents/${documentId}/pdf`, { responseType: "blob" })
        .then((r) => r.data as Blob),
    exportSummaryPdf: (documentId: string) =>
      http
        .get(`/api/v1/export/documents/${documentId}/summary/pdf`, { responseType: "blob" })
        .then((r) => r.data as Blob),
  };
}

export interface ApiClient {
  getLoginUrl: () => Promise<{ url: string }>;
  getLoginUrlForMobile: (redirectUri: string) => Promise<{ url: string }>;
  exchangeCode: (code: string, redirectUri?: string) => Promise<{ access_token: string; token_type: string }>;
  getMe: () => Promise<User>;
  getProfile: () => Promise<User>;
  updateSettings: (data: UserSettingsUpdate) => Promise<User>;
  listDocuments: () => Promise<Document[]>;
  getDocument: (id: string) => Promise<Document>;
  uploadDocument: (file: FormData) => Promise<Document>;
  updateDocumentSettings: (id: string, data: DocumentSettingsUpdate) => Promise<Document>;
  patchDocumentContent: (id: string, patch: DocumentContentPatch) => Promise<Document>;
  deleteDocument: (id: string) => Promise<void>;
  listHighlights: (documentId: string) => Promise<Highlight[]>;
  createHighlight: (documentId: string, data: HighlightCreate) => Promise<Highlight>;
  updateHighlight: (documentId: string, highlightId: string, data: HighlightUpdate) => Promise<Highlight>;
  deleteHighlight: (documentId: string, highlightId: string) => Promise<void>;
  clearHighlights: (documentId: string) => Promise<void>;
  getSummary: (documentId: string) => Promise<SummarySection[]>;
  exportDocumentPdf: (documentId: string) => Promise<Blob>;
  exportSummaryPdf: (documentId: string) => Promise<Blob>;
}
