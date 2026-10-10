import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileSpreadsheet, X, ArrowRight } from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';

export function UploadPage() {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<{
    name: string;
    size: string;
    rows: string;
  } | null>({
    name: 'October_Transactions.xlsx',
    size: '2.4 MB',
    rows: '12,450 rows',
  });

  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setSelectedFile({
      name: 'October_Transactions.xlsx',
      size: '2.4 MB',
      rows: '12,450 rows',
    });
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-[800px] py-4">
        {/* Page Heading */}
        <div className="text-center">
          <h1 className="font-serif text-3xl font-normal text-[#F1E7CF] sm:text-4xl">
            Upload your transaction data
          </h1>
          <p className="mt-2 text-sm text-[#B9AD92]">
            Supported formats: XLSX, CSV (structured data)
          </p>
        </div>

        {/* Drop Zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => {
            if (!selectedFile) {
              setSelectedFile({
                name: 'October_Transactions.xlsx',
                size: '2.4 MB',
                rows: '12,450 rows',
              });
            }
          }}
          className={`mt-10 flex min-h-[260px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 text-center transition-all duration-300 ${
            isDragging
              ? 'border-[#C8A85A] bg-[#1D1810]'
              : 'border-[rgba(200,168,90,0.22)] bg-[#17130D]/70 hover:border-[rgba(200,168,90,0.45)] hover:bg-[#17130D]'
          }`}
        >
          <div className="flex size-14 items-center justify-center rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#100D08] text-[#C8A85A]">
            <Upload className="size-6" />
          </div>

          <p className="mt-5 text-base font-medium text-[#F1E7CF]">
            Drag and drop your file here
          </p>
          <p className="mt-1 text-xs text-[#B9AD92]">
            or click <span className="text-[#C8A85A] underline">to browse</span>
          </p>
          <p className="mt-4 text-[11px] text-[#756B58]">
            XLSX, CSV (Max 50MB)
          </p>
        </div>

        {/* Selected File Card */}
        {selectedFile && (
          <div className="mt-6 flex items-center justify-between rounded-xl border border-[rgba(200,168,90,0.25)] bg-[#17130D] p-4.5 shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
            <div className="flex items-center gap-4">
              <div className="flex size-10 items-center justify-center rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#100D08] text-[#C8A85A]">
                <FileSpreadsheet className="size-5" />
              </div>
              <div>
                <p className="font-mono text-sm font-medium text-[#F1E7CF]">
                  {selectedFile.name}
                </p>
                <p className="mt-0.5 text-xs text-[#B9AD92]">
                  {selectedFile.size} • {selectedFile.rows}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setSelectedFile(null)}
              className="flex size-8 items-center justify-center rounded-lg text-[#756B58] transition-colors hover:bg-[#1D1810] hover:text-[#F1E7CF]"
            >
              <X className="size-4" />
            </button>
          </div>
        )}

        {/* Action Button */}
        <div className="mt-8 flex justify-end">
          <button
            type="button"
            disabled={!selectedFile}
            onClick={() => navigate('/validation')}
            className={`inline-flex min-w-[170px] items-center justify-center gap-2 rounded-lg px-6 py-3 text-sm font-semibold tracking-wide transition-all ${
              selectedFile
                ? 'bg-[#C8A85A] text-[#0A0805] shadow-[0_4px_20px_rgba(200,168,90,0.22)] hover:bg-[#D8BC78]'
                : 'cursor-not-allowed bg-[rgba(200,168,90,0.15)] text-[#756B58]'
            }`}
          >
            <span>Continue</span>
            <ArrowRight className="size-4" />
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
