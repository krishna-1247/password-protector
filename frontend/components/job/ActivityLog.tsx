"use client";

import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, AlertTriangle, XCircle, SkipForward } from "lucide-react";
import type { FileResult } from "@/lib/types";

interface ActivityLogProps {
  results: FileResult[];
  maxVisible?: number;
}

const statusIcon = {
  success: { Icon: CheckCircle2, className: "text-success" },
  missing: { Icon: AlertTriangle, className: "text-amber-500" },
  failed:  { Icon: XCircle,      className: "text-red-500"     },
  skipped: { Icon: SkipForward,  className: "text-slate-400"   },
};

const statusRowStyle = {
  success: "border-success/30",
  missing: "border-amber-500/30",
  failed:  "border-red-500/30",
  skipped: "border-slate-400/20",
};

export function ActivityLog({ results, maxVisible = 200 }: ActivityLogProps) {
  const visible = results.slice(-maxVisible).reverse();

  return (
    <div className="bg-white rounded-2xl overflow-hidden shadow-neo-raised border border-white/60">
      {/* Header */}
      <div className="px-4 py-2 border-b border-slate-100 flex items-center justify-between bg-[#F6F8FC]/50">
        <h3 className="text-xs font-bold text-slate-800">Activity Log</h3>
        <span className="text-[10px] font-semibold text-slate-400">{results.length} entries</span>
      </div>

      {/* Log entries */}
      <div className="max-h-[110px] overflow-y-auto divide-y divide-slate-100">
        <AnimatePresence mode="popLayout" initial={false}>
          {visible.length === 0 ? (
            <div className="px-4 py-6 text-center text-[11px] text-slate-400">
              Processing results will appear here…
            </div>
          ) : (
            visible.map((r, i) => {
              const { Icon, className } = statusIcon[r.status];
              return (
                <motion.div
                  key={`${r.filename}-${i}`}
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i * 0.02, 0.5) }}
                  className={`flex items-center gap-2.5 px-4 py-1.5 border-l-[3px] ${statusRowStyle[r.status]} hover:bg-[#F6F8FC] transition-colors`}
                >
                  <Icon className={`w-3 h-3 flex-shrink-0 ${className}`} />
                  <span className="text-[11px] text-slate-700 font-semibold flex-1 truncate font-mono">
                    {r.filename}
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium truncate max-w-[180px] text-right">
                    {r.message}
                  </span>
                  {r.elapsed_ms > 0 && (
                    <span className="text-[10px] font-semibold text-slate-400 flex-shrink-0 w-14 text-right">
                      {r.elapsed_ms.toFixed(0)}ms
                    </span>
                  )}
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
