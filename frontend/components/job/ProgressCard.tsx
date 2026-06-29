"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import type { JobStatus } from "@/lib/types";

interface ProgressCardProps {
  status: JobStatus;
  progress: number;
  done: number;
  total: number;
  elapsedSec?: number;
  currentFile?: string;
}

const statusConfig = {
  pending: {
    label: "Waiting…",
    icon: Clock,
    iconClass: "text-slate-400",
    badgeClass: "badge-pending",
  },
  processing: {
    label: "Encrypting…",
    icon: Loader2,
    iconClass: "text-brand-500 animate-spin",
    badgeClass: "badge-processing",
  },
  completed: {
    label: "Complete",
    icon: CheckCircle2,
    iconClass: "text-success",
    badgeClass: "badge-completed",
  },
  failed: {
    label: "Failed",
    icon: XCircle,
    iconClass: "text-red-500",
    badgeClass: "badge-failed",
  },
};

export function ProgressCard({
  status,
  progress,
  done,
  total,
  elapsedSec,
  currentFile,
}: ProgressCardProps) {
  const cfg = statusConfig[status];
  const Icon = cfg.icon;

  return (
    <div className="bg-white rounded-2xl p-4 shadow-neo-raised border border-white/60 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className={`w-4.5 h-4.5 ${cfg.iconClass}`} />
          <h3 className="text-xs font-bold text-slate-800">
            Encryption Progress
          </h3>
        </div>
        <div className="flex items-center gap-3">
          {elapsedSec !== undefined && elapsedSec > 0 && (
            <span className="text-[10px] font-semibold text-slate-400">
              {elapsedSec.toFixed(1)}s
            </span>
          )}
          <span className={`badge ${cfg.badgeClass}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${
              status === "processing" ? "bg-brand-500 animate-pulse" :
              status === "completed" ? "bg-success" :
              status === "failed" ? "bg-red-500" : "bg-slate-400"
            }`} />
            {cfg.label}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="space-y-1.5">
        <div className="progress-track h-2">
          <motion.div
            className="progress-fill h-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          />
        </div>

        <div className="flex items-center justify-between text-xs font-medium">
          <AnimatePresence mode="wait">
            {currentFile && status === "processing" ? (
              <motion.span
                key={currentFile}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className="text-slate-400 truncate max-w-[60%]"
              >
                {currentFile}
              </motion.span>
            ) : (
              <span className="text-slate-400">
                {status === "completed" ? "All files processed" : ""}
              </span>
            )}
          </AnimatePresence>

          <motion.span
            key={`${done}/${total}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-slate-600 font-mono font-bold ml-auto"
          >
            {total > 0 ? `${done.toLocaleString()} / ${total.toLocaleString()}` : `${progress}%`}
          </motion.span>
        </div>
      </div>
    </div>
  );
}
