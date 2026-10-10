import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileSpreadsheet, X, ArrowRight, Loader2, AlertCircle } from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { useApp } from '../context/AppContext';

export function UploadPage() {
  const navigate = useNavigate();
  const { processFile } = useApp();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !['xlsx', 'xls', 'csv'].includes(ext)) {
      setError('Please select a valid XLSX or CSV file.');
      return;
    }

    setError(null);
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleContinue = async () => {
    if (!selectedFile) return;

    try {
      setIsUploading(true);
      setError(null);
      await processFile(selectedFile);
      setIsUploading(false);
      navigate('/validation');
    } catch (err: any) {
      setIsUploading(false);
      setError(err.message || 'Failed to parse file. Please verify format and contents.');
    }
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-[840px] py-4">
        {/* Page Heading */}
        <div className="text-center">
          <h1 className="font-serif text-3xl font-normal text-[#F0E5CA] sm:text-4xl">
            Upload your transaction data
          </h1>
          <p className="mt-2 text-base text-[#B9AD92]">
            Supported formats: XLSX, CSV (structured transaction data)
          </p>
        </div>

        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFileSelect(e.target.files[0]);
            }
          }}
          className="hidden"
        />

        {/* Drop Zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`mt-10 flex min-h-[280px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 text-center transition-all duration-300 ${
            isDragging
              ? 'border-[#C8A85A] bg-[#1D1810]'
              : 'border-[rgba(200,168,90,0.25)] bg-[#17130D]/80 hover:border-[#C8A85A] hover:bg-[#17130D]'
          }`}
        >
          <div className="flex size-16 items-center justify-center rounded-2xl border border-[rgba(200,168,90,0.35)] bg-[#100D08] text-[#C8A85A]">
            <Upload className="size-7" />
          </div>

          <p className="mt-6 text-lg font-medium text-[#F0E5CA]">
            Drag and drop your file here
          </p>
          <p className="mt-1.5 text-sm text-[#B9AD92]">
            or click <span className="text-[#C8A85A] underline font-medium">to browse from device</span>
          </p>
          <p className="mt-4 text-xs text-[#756B58]">
            XLSX, CSV (Max 50MB)
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mt-6 flex items-center gap-3 rounded-xl border border-[#8B3A3A] bg-[#8B3A3A]/15 p-4 text-sm text-[#D48080]">
            <AlertCircle className="size-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Selected File Card */}
        {selectedFile && (
          <div className="mt-6 flex items-center justify-between rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#17130D] p-5 shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
            <div className="flex items-center gap-4">
              <div className="flex size-12 items-center justify-center rounded-xl border border-[rgba(200,168,90,0.25)] bg-[#100D08] text-[#C8A85A]">
                <FileSpreadsheet className="size-6" />
              </div>
              <div>
                <p className="font-mono text-base font-medium text-[#F0E5CA]">
                  {selectedFile.name}
                </p>
                <p className="mt-0.5 text-xs text-[#B9AD92]">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
              }}
              className="flex size-9 items-center justify-center rounded-lg text-[#756B58] transition-colors hover:bg-[#1D1810] hover:text-[#F0E5CA]"
            >
              <X className="size-5" />
            </button>
          </div>
        )}

        {/* Action Button */}
        <div className="mt-8 flex justify-end">
          <button
            type="button"
            disabled={!selectedFile || isUploading}
            onClick={handleContinue}
            className={`inline-flex min-w-[190px] h-[54px] items-center justify-center gap-2.5 rounded-xl px-7 text-base font-semibold tracking-wide transition-all ${
              selectedFile && !isUploading
                ? 'bg-[#D8BC78] text-[#090704] shadow-[0_4px_20px_rgba(200,168,90,0.25)] hover:bg-[#E8D29A]'
                : 'cursor-not-allowed bg-[rgba(200,168,90,0.15)] text-[#756B58]'
            }`}
          >
            {isUploading ? (
              <>
                <Loader2 className="size-5 animate-spin" />
                <span>Reading File...</span>
              </>
            ) : (
              <>
                <span>Continue</span>
                <ArrowRight className="size-5" />
              </>
            )}
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
