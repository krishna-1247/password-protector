"use client";

import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Table2, X, CheckCircle2 } from "lucide-react";

interface ExcelUploadProps {
  file: File | null;
  onFileSelected: (file: File | null) => void;
  disabled?: boolean;
  className?: string;
}

const ALLOWED = [".xlsx", ".xls", ".csv"];

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ExcelUpload({ file, onFileSelected, disabled, className = "" }: ExcelUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = useCallback((f: File): boolean => {
    setError(null);
    const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
    if (!ALLOWED.includes(ext)) {
      setError(`Invalid file type. Use .xlsx, .xls, or .csv`);
      return false;
    }
    return true;
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      const f = e.dataTransfer.files[0];
      if (f && validate(f)) onFileSelected(f);
    },
    [disabled, onFileSelected, validate]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f && validate(f)) onFileSelected(f);
      e.target.value = "";
    },
    [onFileSelected, validate]
  );

  return (
    <div className="space-y-2">
      <motion.div
        whileHover={!disabled ? { scale: 1.002 } : {}}
        onDragOver={(e) => { e.preventDefault(); !disabled && setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`
          border border-dashed rounded-2xl py-3 px-4 text-center cursor-pointer
          transition-all duration-300 select-none flex flex-col justify-center items-center
          ${className || "h-[110px]"}
          ${isDragging
            ? "drag-active border-success-500"
            : "border-slate-300 bg-[#F6F8FC] shadow-neo-inset hover:shadow-neo-raised-sm hover:bg-white hover:border-success-500/50"
          }
          ${disabled ? "opacity-50 cursor-not-allowed" : ""}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          className="hidden"
          onChange={handleChange}
          disabled={disabled}
        />

        <AnimatePresence mode="wait">
          {file ? (
            <motion.div
              key="file"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex items-center justify-between gap-3 w-full px-2"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-white shadow-neo-raised-sm border border-white flex items-center justify-center">
                  <CheckCircle2 className="w-4.5 h-4.5 text-success" />
                </div>
                <div className="text-left">
                  <p className="text-xs font-semibold text-slate-800 truncate max-w-[180px]">
                    {file.name}
                  </p>
                  <p className="text-[10px] font-medium text-slate-400">{formatBytes(file.size)}</p>
                </div>
              </div>
              {!disabled && (
                <button
                  onClick={(e) => { e.stopPropagation(); onFileSelected(null); }}
                  className="p-1.5 rounded-lg hover:bg-red-50 hover:text-red-500 text-slate-400 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center gap-2.5"
            >
              <div className="p-2.5 rounded-xl bg-white shadow-neo-raised-sm border border-white flex items-center justify-center">
                <Table2 className="w-5.5 h-5.5 text-slate-400" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-800">
                  Drop Excel / CSV file
                </p>
                <p className="text-[10px] font-medium text-slate-400 mt-1">
                  .xlsx, .xls, or .csv • With PDF filename & password columns
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      <AnimatePresence>
        {error && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-[10px] text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-1.5 shadow-neo-raised-sm flex items-center gap-1.5"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />
            {error}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}
