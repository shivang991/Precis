export type NodeType =
  | "heading"
  | "paragraph"
  | "list_item"
  | "table"
  | "image"
  | "code";

export type HeadingLevel = 1 | 2 | 3 | 4 | 5 | 6;

export interface BaseNode {
  id: string;
  type: NodeType;
  children?: DocumentNode[];
}

export interface HeadingNode extends BaseNode {
  type: "heading";
  level: HeadingLevel;
  text: string;
  children: DocumentNode[];
}

export interface ParagraphNode extends BaseNode {
  type: "paragraph";
  text: string;
}

export interface ListItemNode extends BaseNode {
  type: "list_item";
  text: string;
  depth: number;
}

export interface TableNode extends BaseNode {
  type: "table";
  headers: string[];
  rows: string[][];
}

export interface ImageNode extends BaseNode {
  type: "image";
  caption?: string;
  storage_key?: string;
}

export interface CodeNode extends BaseNode {
  type: "code";
  text: string;
  language?: string;
}

export type DocumentNode =
  | HeadingNode
  | ParagraphNode
  | ListItemNode
  | TableNode
  | ImageNode
  | CodeNode;

export interface StandardFormat {
  title: string;
  author?: string;
  page_count?: number;
  source_type: "DIGITAL" | "SCANNED";
  created_at: string;
  nodes: DocumentNode[];
}
