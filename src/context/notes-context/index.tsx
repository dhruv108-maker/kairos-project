import { createContext, useState, type ReactNode } from "react";
import type { notesType } from "src/types/apps/notes";

interface NotesContextType {
  notes: notesType[];
  loading: boolean;
  error: Error | null;
  selectedNoteId: number;
  selectNote: (id: number) => void;
  addNote: (newNote: notesType) => Promise<void>;
  updateNote: (id: number, title: string, color: string) => Promise<void>;
  deleteNote: (id: number) => Promise<void>;
}

const initialNotes: notesType[] = [
  {
    id: 1,
    color: "primary",
    title: "Welcome to Notes. Add a note to capture something important.",
    datef: new Date().toISOString(),
    deleted: false,
  },
];

const initialContext: NotesContextType = {
  notes: initialNotes,
  loading: false,
  error: null,
  selectedNoteId: 1,
  selectNote: () => {},
  addNote: async () => {},
  updateNote: async () => {},
  deleteNote: async () => {},
};

export const NotesContext = createContext<NotesContextType>(initialContext);

export function NotesProvider({ children }: { children: ReactNode }) {
  const [notes, setNotes] = useState<notesType[]>(initialNotes);
  const [selectedNoteId, setSelectedNoteId] = useState(1);

  const addNote = async (newNote: notesType) => {
    const note: notesType = {
      ...newNote,
      id: Math.max(0, ...notes.map((item) => item.id)) + 1,
      datef: new Date().toISOString(),
      deleted: false,
    };
    setNotes((current) => [...current, note]);
    setSelectedNoteId(note.id);
  };

  const updateNote = async (id: number, title: string, color: string) => {
    setNotes((current) =>
      current.map((note) => note.id === id ? { ...note, title, color } : note),
    );
  };

  const deleteNote = async (id: number) => {
    const remaining = notes.filter((note) => note.id !== id);
    setNotes(remaining);
    if (selectedNoteId === id) setSelectedNoteId(remaining[0]?.id ?? 0);
  };

  return (
    <NotesContext.Provider
      value={{
        notes,
        loading: false,
        error: null,
        selectedNoteId,
        selectNote: setSelectedNoteId,
        addNote,
        updateNote,
        deleteNote,
      }}
    >
      {children}
    </NotesContext.Provider>
  );
}
