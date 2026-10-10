export type VoucherType = 'Purchase' | 'Sales' | 'Payment' | 'Expense' | 'Journal';
export type ConfidenceLevel = 'High' | 'Review' | 'Exception';

export interface TopCandidate {
  voucher: VoucherType;
  confidence: number;
}

export interface AIAnalysis {
  classificationBasis: string;
  candidateComparison: string;
  confidenceFactors: string[];
  detectedSignals: string[];
}

export interface Transaction {
  id: string;
  invoiceNo: string;
  date: string;
  party: string;
  amount: string;
  rawAmount: number;
  predictedVoucher: VoucherType;
  confidence: number;
  status: ConfidenceLevel;
  gstin: string;
  taxableValue: string;
  gstAmount: string;
  paymentMode: string;
  description: string;
  sourceFile: string;
  topCandidates: TopCandidate[];
  aiAnalysis: AIAnalysis;
  isVerified?: boolean;
}

export interface UploadRecord {
  id: string;
  filename: string;
  rows: string;
  status: 'Completed' | 'Processing' | 'Failed';
  date: string;
}

export interface ValidationCheck {
  id: string;
  label: string;
  status: 'passed' | 'warning' | 'failed';
  iconType: 'check' | 'warning' | 'file';
}
