"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  ShieldCheck, Download, Lock, Zap, Server,
  ChevronRight, Settings2, ArrowRight, FileDown,
} from "lucide-react";

import { Header } from "@/components/layout/Header";
import { DropZone } from "@/components/upload/DropZone";
import { ExcelUpload } from "@/components/upload/ExcelUpload";
import { ProgressCard } from "@/components/job/ProgressCard";
import { StatsRow } from "@/components/job/StatsRow";
import { ActivityLog } from "@/components/job/ActivityLog";
import { useJobPoller } from "@/hooks/useJobPoller";
import { uploadFiles, processJob, getDownloadUrl } from "@/lib/api";
import type { JobStats } from "@/lib/types";

type AppState = "idle" | "uploading" | "processing" | "done" | "error";

const EMPTY_STATS: JobStats = {
  total: 0, success: 0, missing: 0, failed: 0, skipped: 0, elapsed_sec: 0,
};

export default function HomePage() {
  const [pdfFiles, setPdfFiles] = useState<File[]>([]);
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [appState, setAppState] = useState<AppState>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Settings
  const [skipEncrypted, setSkipEncrypted] = useState(true);
  const [maxWorkers, setMaxWorkers] = useState(4);
  const [showSettings, setShowSettings] = useState(false);

  // Live job polling
  const { status: jobStatus } = useJobPoller(jobId);

  // Sync app state from poll results using useEffect to avoid render side-effects
  useEffect(() => {
    if (!jobStatus || !jobId) return;

    if (jobStatus.status === "completed" && appState === "processing") {
      setAppState("done");
      setDownloadUrl(getDownloadUrl(jobId));
      toast.success(
        `Done! ${jobStatus.stats.success} PDF(s) encrypted in ${jobStatus.stats.elapsed_sec.toFixed(1)}s`
      );
    } else if (jobStatus.status === "failed" && appState === "processing") {
      setAppState("error");
      setErrorMsg(jobStatus.error ?? "Unknown error");
      toast.error(`Encryption failed: ${jobStatus.error}`);
    }
  }, [jobStatus, appState, jobId]);

  const handleAddPdfs = useCallback((incoming: File[]) => {
    setPdfFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      const newFiles = incoming.filter((f) => !existing.has(f.name));
      return [...prev, ...newFiles];
    });
  }, []);

  const handleRemovePdf = useCallback((idx: number) => {
    setPdfFiles((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const handleEncrypt = async () => {
    if (!pdfFiles.length || !excelFile) return;

    setAppState("uploading");
    setErrorMsg(null);
    setDownloadUrl(null);
    setJobId(null);

    try {
      // 1. Upload
      toast.loading("Uploading files…", { id: "upload" });
      const uploadResp = await uploadFiles(pdfFiles, excelFile);
      toast.dismiss("upload");
      toast.success(`Uploaded ${uploadResp.file_count} PDFs`);

      // 2. Start processing
      await processJob(uploadResp.job_id, {
        skip_encrypted: skipEncrypted,
        max_workers: maxWorkers,
        overwrite: true,
      });

      setJobId(uploadResp.job_id);
      setAppState("processing");
    } catch (err) {
      toast.dismiss("upload");
      const msg = err instanceof Error ? err.message : "Upload failed";
      toast.error(msg);
      setErrorMsg(msg);
      setAppState("error");
    }
  };

  const handleReset = () => {
    setPdfFiles([]);
    setExcelFile(null);
    setAppState("idle");
    setJobId(null);
    setDownloadUrl(null);
    setErrorMsg(null);
  };

  const isLocked = appState === "uploading" || appState === "processing";
  const canEncrypt = pdfFiles.length > 0 && excelFile !== null && !isLocked;

  const currentStats = jobStatus?.stats ?? EMPTY_STATS;
  const currentProgress = jobStatus?.progress ?? 0;
  const currentDone = jobStatus?.done ?? 0;
  const currentTotal = jobStatus?.total ?? 0;  return (
    <div className="h-screen flex flex-col bg-[#F6F8FC] overflow-hidden select-none">
      <Header />

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 flex flex-col justify-between py-4 overflow-hidden">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="text-center flex flex-col items-center mt-2 space-y-2"
        >
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white shadow-neo-raised-sm text-[10px] text-brand-600 font-bold border border-white">
            <Zap className="w-3 h-3 text-brand-500" />
            Bulk PDF Encryption · AES-256 · No database
          </div>
          <h2 className="text-2xl md:text-[38px] font-bold text-slate-900 tracking-tight leading-none">
            Protect Thousands of PDFs{" "}
            <span className="text-brand-500">
              in Seconds
            </span>
          </h2>
          <p className="text-slate-500 max-w-lg mx-auto text-xs leading-normal">
            Upload your PDFs and a mapping Excel sheet. We encrypt each one with
            its password and return a single downloadable ZIP — no data stored.
          </p>
        </motion.div>

        {/* Feature pills */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="flex flex-wrap justify-center gap-3 mt-3"
        >
          {[
            { icon: Lock, label: "AES-256 Encryption" },
            { icon: Zap, label: "Multi-threaded" },
            { icon: Server, label: "Stateless API" },
            { icon: ShieldCheck, label: "Files auto-deleted" },
          ].map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-2 px-3 py-1 rounded-full bg-white shadow-neo-raised-sm text-[10px] font-semibold text-slate-600 border border-white/60"
            >
              <Icon className="w-3 h-3 text-brand-500" />
              {label}
            </div>
          ))}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="w-full h-[clamp(380px,56vh,460px)] bg-white rounded-[20px] shadow-neo-raised-lg p-6 border border-white/80 flex flex-col justify-between overflow-hidden mt-4"
        >
          {appState === "idle" || appState === "uploading" ? (
            <div className="flex-grow flex flex-col justify-between h-full overflow-hidden">
              {/* Upload grid */}
              <div className="grid md:grid-cols-2 gap-6 items-start">
                {/* PDFs */}
                <div className="space-y-1.5">
                  <label className="text-[12px] font-bold text-slate-500 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-500" />
                    PDF Files
                  </label>
                  <DropZone
                    files={pdfFiles}
                    onFilesSelected={handleAddPdfs}
                    onRemove={handleRemovePdf}
                    disabled={isLocked}
                    className={showSettings ? "h-[75px]" : "h-[110px]"}
                  />
                </div>

                {/* Excel */}
                <div className="space-y-1.5">
                  <label className="text-[12px] font-bold text-slate-500 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-success-500" />
                    Password Mapping (Excel / CSV)
                  </label>
                  <ExcelUpload
                    file={excelFile}
                    onFileSelected={setExcelFile}
                    disabled={isLocked}
                    className={showSettings ? "h-[75px]" : "h-[110px]"}
                  />

                  {/* Format hint */}
                  <div className="rounded-xl bg-[#F6F8FC] shadow-neo-inset p-3 text-[10px] text-slate-600 space-y-1.5 border border-white/40">
                    <div className="flex items-center justify-between">
                      <p className="font-semibold text-slate-700">Expected columns:</p>
                      <a
                        href="/template.xlsx"
                        download="template.xlsx"
                        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-xl bg-white border border-slate-200 text-slate-600 hover:text-brand-500 hover:border-brand-500/40 text-[9px] font-bold shadow-neo-raised-sm hover:shadow-neo-raised-md transition-all h-[26px] select-none"
                      >
                        <FileDown className="w-3 h-3 text-brand-500" />
                        Download Template
                      </a>
                    </div>
                    <div className="font-mono grid grid-cols-2 gap-x-4 gap-y-0.5 bg-white/40 p-2 rounded-lg border border-white">
                      <span className="text-brand-600 font-semibold">PDF File</span>
                      <span className="text-success-600 font-semibold">Password</span>
                      <span>Rahul.pdf</span>
                      <span className="text-slate-500">ABCDE1234F</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Settings toggle */}
              <div className="pt-2">
                <button
                  onClick={() => setShowSettings((s) => !s)}
                  className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 hover:text-brand-500 transition-colors py-0.5"
                >
                  <Settings2 className="w-3 h-3" />
                  Advanced Settings
                  <ChevronRight
                    className={`w-3 h-3 transition-transform ${showSettings ? "rotate-90" : ""}`}
                  />
                </button>

                <AnimatePresence>
                  {showSettings && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-2 grid sm:grid-cols-2 gap-6 p-3.5 rounded-xl bg-[#F6F8FC] shadow-neo-inset border border-white/40 items-center"
                    >
                      {/* Workers */}
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <p className="text-[11px] font-semibold text-slate-700">
                            Parallel Workers
                          </p>
                          <p className="text-[9px] font-medium text-slate-400">
                            Thread count: {maxWorkers}
                          </p>
                        </div>
                        <input
                          type="range"
                          min={1}
                          max={16}
                          value={maxWorkers}
                          onChange={(e) => setMaxWorkers(Number(e.target.value))}
                          disabled={isLocked}
                          className="flex-1 max-w-[120px] h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-500"
                        />
                      </div>

                      {/* Skip encrypted */}
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <p className="text-[11px] font-semibold text-slate-700">
                            Skip already-encrypted PDFs
                          </p>
                          <p className="text-[9px] font-medium text-slate-400">
                            Prevents double-encryption
                          </p>
                        </div>
                        <button
                          onClick={() => setSkipEncrypted((v) => !v)}
                          disabled={isLocked}
                          className={`relative w-9 h-5 rounded-full transition-colors shadow-neo-inset border flex-shrink-0 ${
                            skipEncrypted
                              ? "bg-brand-500 border-brand-500"
                              : "bg-slate-200 border-slate-300"
                          }`}
                        >
                          <span
                            className={`absolute top-[2px] w-3.5 h-3.5 bg-white rounded-full shadow transition-all ${
                              skipEncrypted ? "left-[18px]" : "left-[2px]"
                            }`}
                          />
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Action button */}
              <div className="pt-2">
                <motion.button
                  whileTap={canEncrypt ? { scale: 0.99 } : {}}
                  onClick={handleEncrypt}
                  disabled={!canEncrypt}
                  className={`
                    w-full flex items-center justify-center gap-2 py-3 px-6
                    rounded-xl font-bold text-xs transition-all duration-150 select-none h-11
                    ${canEncrypt
                      ? "bg-brand-500 hover:bg-brand-600 text-white shadow-neo-raised hover:shadow-neo-raised-lg active:shadow-neo-inset"
                      : "bg-[#F6F8FC] text-slate-400 border border-slate-200 cursor-not-allowed shadow-neo-inset"
                    }
                  `}
                >
                  {appState === "uploading" ? (
                    <>
                      <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Uploading files…
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4" />
                      Encrypt {pdfFiles.length > 0 ? `${pdfFiles.length} PDF${pdfFiles.length > 1 ? "s" : ""}` : "PDFs"}
                      <ArrowRight className="w-3.5 h-3.5 ml-1" />
                    </>
                  )}
                </motion.button>
              </div>

              {/* Validation hints */}
              {!pdfFiles.length && !excelFile && (
                <p className="text-center text-[10px] text-slate-400 font-semibold mt-1">
                  Upload PDFs and an Excel file to get started
                </p>
              )}
              {pdfFiles.length > 0 && !excelFile && (
                <p className="text-center text-[10px] text-amber-600 font-semibold mt-1">
                  Add the Excel/CSV password mapping file
                </p>
              )}
              {!pdfFiles.length && excelFile && (
                <p className="text-center text-[10px] text-amber-600 font-semibold mt-1">
                  Add at least one PDF file
                </p>
              )}
            </div>
          ) : (
            <div className="flex-grow flex flex-col justify-between h-full overflow-hidden gap-3">
              {/* Progress */}
              <ProgressCard
                status={jobStatus?.status ?? "processing"}
                progress={currentProgress}
                done={currentDone}
                total={currentTotal}
                elapsedSec={currentStats.elapsed_sec}
              />

              {/* Stats */}
              <StatsRow stats={currentStats} total={currentTotal} />

              {/* Activity log */}
              <div className="flex-grow overflow-hidden">
                <ActivityLog results={jobStatus?.results ?? []} />
              </div>

              {/* Error */}
              {appState === "error" && errorMsg && (
                <div className="flex items-start gap-2.5 p-2.5 rounded-xl bg-red-50 border border-red-100 shadow-neo-raised-sm">
                  <div className="w-1.5 h-1.5 mt-1 rounded-full bg-red-500 flex-shrink-0" />
                  <p className="text-[10px] font-semibold text-red-600 truncate">{errorMsg}</p>
                </div>
              )}

              {/* Download + Reset */}
              <div className="flex gap-3 pt-1">
                <AnimatePresence>
                  {downloadUrl && appState === "done" && (
                    <motion.a
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      href={downloadUrl}
                      download="encrypted_pdfs.zip"
                      className="flex-1 flex items-center justify-center gap-2 py-3 px-6
                        rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-bold
                        text-xs shadow-neo-raised hover:shadow-neo-raised-lg active:shadow-neo-inset transition-all h-11"
                    >
                      <Download className="w-4 h-4" />
                      Download Encrypted ZIP
                    </motion.a>
                  )}
                </AnimatePresence>

                {(appState === "done" || appState === "error") && (
                  <motion.button
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    onClick={handleReset}
                    className="px-6 py-3 rounded-xl bg-white border border-white/60
                      text-slate-600 hover:text-brand-500 hover:border-brand-500/40 text-xs
                      font-bold shadow-neo-raised hover:shadow-neo-raised-lg transition-all h-11"
                  >
                    Start New Batch
                  </motion.button>
                )}
              </div>
            </div>
          )}
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="w-full px-6 pb-3 mt-auto h-11 flex items-center">
        <div className="w-full max-w-5xl mx-auto px-6 py-3.5 flex flex-col sm:flex-row items-center justify-between bg-white rounded-2xl shadow-neo-raised border border-white/60 text-[10px] text-slate-400 font-semibold gap-3 h-9">
          <p>PDF Protector · No Database · Files deleted after 30 min</p>
          <div className="flex items-center gap-2 text-success-600 bg-success-50/50 px-2 py-0.5 rounded-full border border-success-100">
            <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            All processing is private
          </div>
        </div>
      </footer>
    </div>
  );
}

