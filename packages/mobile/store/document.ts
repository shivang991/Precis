import { create } from "zustand";

type HighlightMode = "view" | "highlight";

interface DocumentUIState {
  highlightMode: HighlightMode;
  activeColor: string;
  setHighlightMode: (mode: HighlightMode) => void;
  setActiveColor: (color: string) => void;
}

export const useDocumentStore = create<DocumentUIState>((set) => ({
  highlightMode: "view",
  activeColor: "yellow",
  setHighlightMode: (mode) => set({ highlightMode: mode }),
  setActiveColor: (color) => set({ activeColor: color }),
}));
