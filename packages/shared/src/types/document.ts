import type { DocumentContentTree } from "./document-content-tree";

export type DocumentStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED";
export type DocumentSourceType = "DIGITAL" | "SCANNED";

export interface Document {
  id: string;
  title: string;
  source_type: DocumentSourceType;
  status: DocumentStatus;
  document_content_tree?: DocumentContentTree;
  created_at: string;
  updated_at: string;
}

export interface DocumentSettingsUpdate {
  title?: string;
}

export interface DocumentContentPatch {
  node_id: string;
  text: string;
}
