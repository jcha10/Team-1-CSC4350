import { motion } from "framer-motion";
import AnimatedNumber from "./AnimatedNumber";

/**
 * Top-of-dashboard summary tiles. Every number here is derived from data
 * the page already fetched (employees + the activity feed) - no new
 * backend endpoint, just aggregation for a faster at-a-glance read.
 */
export default function KpiTiles({ employees, events }) {
  const totalEmployees = employees.length;
  const flaggedNow = employees.filter((e) => e.is_disloyal).length;
  const totalViolations = employees.reduce((sum, e) => sum + e.disloyal_violation_count, 0);

  const keywordCounts = {};
  events.forEach((e) => {
    if (e.is_flagged && e.matched_keyword) {
      keywordCounts[e.matched_keyword] = (keywordCounts[e.matched_keyword] || 0) + 1;
    }
  });
  const topKeyword = Object.entries(keywordCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";

  const tiles = [
    { label: "Employees Monitored", value: totalEmployees, decimals: 0 },
    { label: "Currently Flagged", value: flaggedNow, decimals: 0, accent: flaggedNow > 0 },
    { label: "Total Violations", value: totalViolations, decimals: 0 },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {tiles.map((t, i) => (
        <motion.div
          key={t.label}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: i * 0.05 }}
          className={`rounded-2xl border p-4 shadow-lg ${
            t.accent ? "bg-red-950/50 border-red-700" : "bg-gray-900 border-red-900/50"
          }`}
        >
          <p className="text-xs uppercase tracking-wide text-gray-400">{t.label}</p>
          <p className={`text-3xl font-extrabold tabular-nums ${t.accent ? "text-red-400" : "text-gray-100"}`}>
            <AnimatedNumber value={t.value} decimals={t.decimals} />
          </p>
        </motion.div>
      ))}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.15 }}
        className="rounded-2xl border bg-gray-900 border-red-900/50 p-4 shadow-lg"
      >
        <p className="text-xs uppercase tracking-wide text-gray-400">Top Restricted Keyword</p>
        <p className="text-2xl font-extrabold text-gray-100 truncate">{topKeyword}</p>
      </motion.div>
    </div>
  );
}
