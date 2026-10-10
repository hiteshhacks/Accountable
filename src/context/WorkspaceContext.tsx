import React, { createContext, useContext, useEffect, useState } from 'react';
import type { ClassScore, GstAnalysis, InputRecord } from '../api/vyom';

/** One row classified by the VYOM API (manual entry or uploaded file). */
export interface ClassifiedRow {
  id: string;
  source: 'manual' | 'file';
  fileName: string | null;
  sourceRef: string;            // e.g. "Sheet1!R2" or "Manual entry"
  createdAt: string;            // ISO timestamp
  record: InputRecord;          // fields sent to the classifier
  category: string;
  score: number | null;         // uncalibrated
  top: ClassScore[];
}

export interface UploadEntry {
  id: string;
  fileName: string;
  rows: number;
  createdAt: string;
}

export interface SavedAnalysis {
  analysis: GstAnalysis;
  sourceLabel: string;
  createdAt: string;
}

type Theme = 'light' | 'dark';

interface WorkspaceState {
  rows: ClassifiedRow[];
  uploads: UploadEntry[];
  analysis: SavedAnalysis | null;
  businessGstin: string;
  theme: Theme;
  addRows: (rows: ClassifiedRow[], upload?: UploadEntry) => void;
  setAnalysis: (analysis: SavedAnalysis | null) => void;
  setBusinessGstin: (gstin: string) => void;
  toggleTheme: () => void;
  clearWorkspace: () => void;
}

const STORAGE_KEY = 'vyom_workspace_v1';
const THEME_KEY = 'vyom_theme';
const MAX_ROWS = 5000;

interface Stored {
  rows: ClassifiedRow[];
  uploads: UploadEntry[];
  analysis: SavedAnalysis | null;
  businessGstin: string;
}

function load(): Stored {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { rows: [], uploads: [], analysis: null, businessGstin: '', ...JSON.parse(raw) };
  } catch {
    /* corrupt or unavailable storage: start empty */
  }
  return { rows: [], uploads: [], analysis: null, businessGstin: '' };
}

function loadTheme(): Theme {
  try {
    return localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

const WorkspaceContext = createContext<WorkspaceState | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<Stored>(load);
  const [theme, setTheme] = useState<Theme>(loadTheme);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* storage full or blocked: keep working in memory */
    }
  }, [state]);

  useEffect(() => {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  const value: WorkspaceState = {
    ...state,
    theme,
    addRows: (rows, upload) =>
      setState((s) => ({
        ...s,
        rows: [...rows, ...s.rows].slice(0, MAX_ROWS),
        uploads: upload ? [upload, ...s.uploads].slice(0, 50) : s.uploads,
      })),
    setAnalysis: (analysis) => setState((s) => ({ ...s, analysis })),
    setBusinessGstin: (businessGstin) => setState((s) => ({ ...s, businessGstin })),
    toggleTheme: () => setTheme((t) => (t === 'light' ? 'dark' : 'light')),
    clearWorkspace: () => setState((s) => ({ ...s, rows: [], uploads: [], analysis: null })),
  };

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error('useWorkspace must be used within a WorkspaceProvider');
  return ctx;
}

/** Case-insensitive lookup of the first present field among candidate column names. */
export function pickField(record: InputRecord, candidates: string[]): string | null {
  const lower = new Map(Object.keys(record).map((k) => [k.trim().toLowerCase(), k]));
  for (const c of candidates) {
    const key = lower.get(c.toLowerCase());
    if (key !== undefined) {
      const v = record[key];
      if (v !== null && v !== undefined && String(v).trim() !== '') return String(v);
    }
  }
  return null;
}

export const INVOICE_FIELDS = ['Invoice No', 'Invoice Number', 'Document Number', 'Bill No', 'PO Number', 'SO Number',
  'Delivery Challan No', 'GRN Number', 'Payment ID', 'Receipt ID', 'Contra ID', 'Journal ID', 'Export Invoice No',
  'Import Bill No', 'Expense Claim No', 'Rejection Note No', 'Voucher No'];
export const PARTY_FIELDS = ['Party', 'Party Name', 'Vendor Name', 'Customer', 'Supplier', 'Vendor/Provider',
  'Payee Organization', 'Payer Organization', 'Exporter', 'Importer', 'Contractor', 'Subcontractor'];
export const AMOUNT_FIELDS = ['Invoice Value', 'Total Amount', 'Total Value', 'Base Amount', 'Taxable Value', 'Amount',
  'Payment Amount', 'Received Amount', 'Transfer Amount', 'Amount Claimed', 'Free on Board Value', 'Cost Insurance Freight'];
export const REVIEW_SCORE_THRESHOLD = 0.5; // same threshold the GST layer uses for ambiguous classifications
