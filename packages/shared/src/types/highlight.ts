export type HighlightColor = "yellow" | "green" | "blue" | "pink" | "purple";

export interface Highlight {
  id: string;
  document_id: string;
  node_id: string;
  start_offset?: number;
  end_offset?: number;
  ancestor_headings: string[];
  color: HighlightColor;
  note?: string;
  created_at: string;
}

export interface HighlightCreate {
  node_id: string;
  start_offset?: number;
  end_offset?: number;
  color: HighlightColor;
  note?: string;
}

export interface HighlightUpdate {
  color?: HighlightColor;
  note?: string;
}

export interface SummarySection {
  ancestor_headings: string[];
  text: string;
  highlight_id: string;
  color: HighlightColor;
  note?: string;
}
