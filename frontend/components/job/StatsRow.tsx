"use client";

import { motion } from "framer-motion";
import type { JobStats } from "@/lib/types";

interface StatsRowProps {
  stats: JobStats;
  total: number;
}

interface StatCard {
  label: string;
  value: number;
  color: string;
  bgColor: string;
  borderColor: string;
}

export function StatsRow({ stats, total }: StatsRowProps) {
  const cards: StatCard[] = [
    {
      label: "Total",
      value: total,
      color: "text-secondary-500",
      bgColor: "bg-secondary-50",
      borderColor: "border-white/60",
    },
    {
      label: "Encrypted",
      value: stats.success,
      color: "text-success-500",
      bgColor: "bg-success-50",
      borderColor: "border-white/60",
    },
    {
      label: "Skipped",
      value: stats.skipped,
      color: "text-amber-500",
      bgColor: "bg-amber-50",
      borderColor: "border-white/60",
    },
    {
      label: "Missing",
      value: stats.missing,
      color: "text-orange-500",
      bgColor: "bg-orange-50",
      borderColor: "border-white/60",
    },
    {
      label: "Failed",
      value: stats.failed,
      color: "text-red-500",
      bgColor: "bg-red-50",
      borderColor: "border-white/60",
    },
  ];

  return (
    <div className="grid grid-cols-5 gap-2.5">
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06 }}
          className={`bg-white rounded-xl p-2.5 shadow-neo-raised border ${card.borderColor}`}
        >
          <motion.p
            key={card.value}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className={`text-lg font-bold tracking-tight ${card.color}`}
          >
            {card.value.toLocaleString()}
          </motion.p>
          <p className="text-[10px] text-slate-400 mt-0.5 font-bold">{card.label}</p>
        </motion.div>
      ))}
    </div>
  );
}
