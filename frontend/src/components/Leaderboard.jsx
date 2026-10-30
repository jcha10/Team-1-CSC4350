import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import AnimatedNumber from "./AnimatedNumber";

const MEDALS = ["🥇", "🥈", "🥉"];

export default function Leaderboard({ metric, metricLabel, entries, loading }) {
  const myIndex = entries.findIndex((e) => e.is_you);
  const myEntry = myIndex === -1 ? null : entries[myIndex];
  const myRank = myIndex === -1 ? null : myIndex + 1;

  // Rank-change arrow: compares this fetch's rank to the last one we saw
  // FOR THIS METRIC. Keyed by metric (not just a bare ref) so switching
  // tabs never shows a stale delta left over from a different metric.
  const prevRanks = useRef({});
  const [trendByMetric, setTrendByMetric] = useState({});

  useEffect(() => {
    if (myRank == null) return;
    setTrendByMetric((prev) => {
      const priorRank = prevRanks.current[metric];
      const delta = priorRank != null ? priorRank - myRank : 0; // positive = moved up
      return { ...prev, [metric]: delta };
    });
    prevRanks.current[metric] = myRank;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [myRank, metric]);

  const trend = trendByMetric[metric] ?? 0;
  const peerAvg = entries.length ? entries.reduce((sum, e) => sum + e.value, 0) / entries.length : null;

  return (
    <div className="bg-white border-4 border-black rounded-2xl p-5 shadow-lg">
      <div className="flex items-start justify-between flex-wrap gap-2 mb-1">
        <h2 className="text-xl font-extrabold text-black flex items-center gap-2">
          🏆 {metricLabel} Leaderboard
        </h2>
        {myRank != null && (
          <span className="flex items-center gap-1 text-sm font-bold bg-yellow-100 border-2 border-black rounded-full px-3 py-0.5">
            Your rank: #{myRank}
            {trend > 0 && <span className="text-green-700">↑{trend}</span>}
            {trend < 0 && <span className="text-red-700">↓{Math.abs(trend)}</span>}
            {trend === 0 && <span className="text-gray-500">–</span>}
          </span>
        )}
      </div>

      {!loading && peerAvg != null && (
        <p className="text-xs text-gray-600 mb-4">
          Visible peer avg: <span className="font-semibold">{peerAvg.toFixed(1)}</span>
          {myEntry && (
            <>
              {" "}
              · you're{" "}
              <span className={`font-semibold ${myEntry.value >= peerAvg ? "text-green-700" : "text-red-700"}`}>
                {myEntry.value >= peerAvg ? "+" : ""}
                {(myEntry.value - peerAvg).toFixed(1)}
              </span>{" "}
              vs. that average
            </>
          )}
        </p>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : entries.length === 0 ? (
        <p className="text-gray-500 text-sm">
          No one is currently sharing this metric publicly.
        </p>
      ) : (
        <ol className="space-y-2">
          <AnimatePresence initial={false}>
            {entries.map((e, i) => (
              <motion.li
                key={e.username}
                layout
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
                className={`flex items-center justify-between rounded-lg px-3 py-2 ${
                  e.is_you ? "bg-yellow-300 border-2 border-black font-bold" : "bg-yellow-50"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className="w-6 text-center">{MEDALS[i] || `#${i + 1}`}</span>
                  {e.username}
                  {e.is_you && <span className="text-xs uppercase tracking-wide text-black/60">(you)</span>}
                </span>
                <span className="font-mono font-bold tabular-nums">
                  <AnimatedNumber value={e.value} decimals={Number.isInteger(e.value) ? 0 : 1} />
                </span>
              </motion.li>
            ))}
          </AnimatePresence>
        </ol>
      )}
    </div>
  );
}
