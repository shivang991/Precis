import type { DocumentContentTree } from "./document-content-tree";

export type DocumentStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED";
export type DocumentSourceType = "DIGITAL" | "SCANNED";

export interface Document {
  id: string;
  title: string;
  source_type: DocumentSourceType;
  status: DocumentStatus;
  theme?: "default" | "dark" | "sepia";
  include_headings_in_summary?: boolean;
  document_content_tree?: DocumentContentTree;
  created_at: string;
  updated_at: string;
}

export interface DocumentSettingsUpdate {
  title?: string;
  theme?: "default" | "dark" | "sepia";
  include_headings_in_summary?: boolean;
}

export interface DocumentContentPatch {
  node_id: string;
  text: string;
}
