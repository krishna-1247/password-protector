"use client";

import { motion } from "framer-motion";
import { ShieldCheck, Zap, Lock } from "lucide-react";

export function Header() {
  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full sticky top-0 z-50 px-6 pt-3 h-16 flex items-center bg-[#F6F8FC]/80 backdrop-blur-md"
    >
      <div className="w-full max-w-6xl mx-auto px-4 py-2 flex items-center justify-between bg-white rounded-2xl shadow-neo-raised border border-white/60">
        {/* Logo + Name */}
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-brand-50 shadow-neo-raised-sm border border-white flex items-center justify-center">
            <ShieldCheck className="w-4.5 h-4.5 text-brand-500" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-900 leading-none">
              PDF Protector
            </h1>
            <p className="text-[10px] text-slate-400 mt-0.5">Bulk Encryption Tool</p>
          </div>
        </div>

        {/* Badges */}
        <div className="hidden sm:flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white shadow-neo-raised-sm text-[11px] font-semibold text-brand-600 border border-white/80">
            <Zap className="w-3 h-3 text-brand-500" />
            <span>AES-256</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white shadow-neo-raised-sm text-[11px] font-semibold text-success-600 border border-white/80">
            <Lock className="w-3 h-3 text-success-500" />
            <span>No data stored</span>
          </div>
        </div>
      </div>
    </motion.header>
  );
}
