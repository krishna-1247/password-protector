"use client";

import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, X, Upload, AlertCircle } from "lucide-react";

interface DropZoneProps {
  onFilesSelected: (files: File[]) => void;
  files: File[];
  onRemove: (index: number) => void;
  disabled?: boolean;
  className?: string;
}

const MAX_SIZE_MB = 500;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DropZone({ onFilesSelected, files, onRemove, disabled, className = "" }: DropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = useCallback((incoming: File[]): File[] => {
    setError(null);
    const invalid = incoming.filter(
      (f) => !f.name.toLowerCase().endsWith(".pdf")
    );
    if (invalid.length > 0) {
      setError(`${invalid.length} non-PDF file(s) ignored.`);
    }
    const oversized = incoming.filter((f) => f.size > MAX_SIZE_BYTES);
    if (oversized.length > 0) {
      setError(`${oversized.length} file(s) exceed ${MAX_SIZE_MB} MB limit.`);
    }
    return incoming.filter(
      (f) => f.name.toLowerCase().endsWith(".pdf") && f.size <= MAX_SIZE_BYTES
    );
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      const dropped = Array.from(e.dataTransfer.files);
      const valid = validate(dropped);
      if (valid.length > 0) onFilesSelected(valid);
    },
    [disabled, onFilesSelected, validate]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = Array.from(e.target.files ?? []);
      const valid = validate(selected);
      if (valid.length > 0) onFilesSelected(valid);
      e.target.value = "";
    },
    [onFilesSelected, validate]
  );

  const totalSize = files.reduce((s, f) => s + f.size, 0);

  return (
    <div className="space-y-2">
      {/* Drop area */}
      <motion.div
        whileHover={!disabled ? { scale: 1.002 } : {}}
        onDragOver={(e) => { e.preventDefault(); !disabled && setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`
          relative border border-dashed rounded-2xl py-3 px-4 text-center cursor-pointer
          transition-all duration-300 select-none flex flex-col justify-center items-center
          ${className || "h-[110px]"}
          ${isDragging
            ? "drag-active border-brand-500"
            : "border-slate-300 bg-[#F6F8FC] shadow-neo-inset hover:shadow-neo-raised-sm hover:bg-white hover:border-brand-500/50"
          }
          ${disabled ? "opacity-50 cursor-not-allowed" : ""}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={handleChange}
          disabled={disabled}
        />

        <motion.div
          animate={isDragging ? { scale: 1.03 } : { scale: 1 }}
          className="flex flex-col items-center gap-2"
        >
          <div className={`p-2.5 rounded-xl transition-all duration-300 shadow-neo-raised-sm ${isDragging ? "bg-brand-50" : "bg-white"}`}>
            <Upload className={`w-5.5 h-5.5 ${isDragging ? "text-brand-500" : "text-slate-400"}`} />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-800">
              {files.length > 0
                ? `${files.length} PDF${files.length > 1 ? "s" : ""} selected`
                : "Drop PDFs here or click to browse"}
            </p>
            <p className="text-[10px] font-medium text-slate-400 mt-1">
              {files.length > 0
                ? `Total: ${formatBytes(totalSize)}`
                : "Supports multiple files • Max 500 MB each"}
            </p>
          </div>
        </motion.div>
      </motion.div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2 text-[10px] text-amber-700 bg-amber-50 border border-amber-100 rounded-xl px-3 py-1.5 shadow-neo-raised-sm"
          >
            <AlertCircle className="w-3 h-3 flex-shrink-0 text-amber-500" />
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* File list */}
      <AnimatePresence mode="popLayout">
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-h-[85px] overflow-y-auto space-y-1.5 pr-1"
          >
            {files.map((file, i) => (
              <motion.div
                key={`${file.name}-${i}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ delay: Math.min(i * 0.03, 0.3) }}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white shadow-neo-raised-sm border border-white/60 group"
              >
                <FileText className="w-3.5 h-3.5 text-brand-500 flex-shrink-0" />
                <span className="text-[11px] text-slate-700 font-medium flex-1 truncate">{file.name}</span>
                <span className="text-[10px] text-slate-400 font-semibold">{formatBytes(file.size)}</span>
                {!disabled && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onRemove(i); }}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 text-slate-400 hover:text-red-500"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
