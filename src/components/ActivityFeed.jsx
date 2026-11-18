import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

export default function ActivityFeed({ events }) {
  const [query, setQuery] = useState("");
  const [flaggedOnly, setFlaggedOnly] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return events.filter((e) => {
      if (flaggedOnly && !e.is_flagged) return false;
      if (!q) return true;
      return (
        e.username.toLowerCase().includes(q) ||
        e.raw_text.toLowerCase().includes(q) ||
        (e.matched_keyword || "").toLowerCase().includes(q)
      );
    });
  }, [events, query, flaggedOnly]);

  return (
    <div className="bg-gray-900 border border-red-900/50 rounded-2xl p-5 shadow-lg h-[420px] flex flex-col">
      <div className="flex items-center justify-between gap-3 mb-2">
        <h2 className="text-lg font-bold text-red-400">Live Activity Feed</h2>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by user or keyword…"
          className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-red-600 w-48"
        />
      </div>
      <label className="flex items-center gap-2 text-xs text-gray-300 mb-3 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={flaggedOnly}
          onChange={(e) => setFlaggedOnly(e.target.checked)}
          className="w-3.5 h-3.5 accent-red-600"
        />
        Flagged only
      </label>
      <div className="overflow-y-auto space-y-1 pr-1 flex-1 font-mono text-xs">
        {filtered.length === 0 && (
          <p className="text-gray-500">{events.length === 0 ? "Waiting for activity…" : "No matches."}</p>
        )}
        <AnimatePresence initial={false}>
          {filtered.map((e, i) => (
            <motion.div
              key={`${e.timestamp}-${e.username}-${i}`}
              layout
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className={`px-2 py-1.5 rounded border-l-4 break-words ${
                e.is_flagged
                  ? "border-red-500 bg-red-950/40 text-red-300"
                  : "border-gray-700 bg-gray-800/40 text-gray-300"
              }`}
            >
              <span className="text-gray-500">{new Date(e.timestamp).toLocaleTimeString()}</span>{" "}
              <span className="font-bold">{e.username}</span> — {e.raw_text}
              {e.is_flagged && (
                <span className="ml-2 uppercase text-[10px] tracking-wide bg-red-600 text-white px-1.5 py-0.5 rounded">
                  flagged: {e.matched_keyword}
                </span>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
