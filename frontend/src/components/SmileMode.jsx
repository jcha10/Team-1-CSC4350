import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { api, METRICS } from "../api";
import useLiveSocket from "../useLiveSocket";
import Leaderboard from "./Leaderboard";
import VisibilitySettings from "./VisibilitySettings";
import AnimatedNumber from "./AnimatedNumber";
import Sparkline from "./Sparkline";

const HISTORY_LENGTH = 20;

export default function SmileMode({ user, setUser, onToast }) {
  const [metric, setMetric] = useState("points");
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState({ points: [], apm: [], total_clicks: [], active_screen_time: [] });
  const metricRef = useRef(metric);
  metricRef.current = metric;

  // `showSpinner` is only for tab switches; live refreshes swap data in
  // place so the list doesn't flash "Loading…" every few seconds.
  async function loadLeaderboard(m, showSpinner = false) {
    if (showSpinner) setLoading(true);
    try {
      const data = await api.getLeaderboard(m);
      if (m === metricRef.current) setEntries(data); // ignore responses for a tab we've left
    } catch (err) {
      if (err.status !== 401) onToast(err.message || "Could not load leaderboard", "error");
    } finally {
      if (showSpinner) setLoading(false);
    }
  }

  useEffect(() => {
    loadLeaderboard(metric, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metric]);

  // One socket for the whole page (not one per tab). Every
  // "leaderboard_tick" refetches whichever tab is open right now.
  useLiveSocket(api.leaderboardSocketUrl, {
    onMessage: () => loadLeaderboard(metricRef.current),
    onReconnect: () => loadLeaderboard(metricRef.current),
  });

  // Also refresh the current user's own numbers periodically so their
  // own point/APM/click counters visibly climb even when hidden from peers.
  useEffect(() => {
    const id = setInterval(() => {
      api.getMe().then(setUser).catch(() => {});
    }, 4000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Rolling client-side history for the sparklines - just the last
  // HISTORY_LENGTH snapshots of each stat, nothing persisted server-side.
  useEffect(() => {
    setHistory((prev) => ({
      points: [...prev.points, user.points].slice(-HISTORY_LENGTH),
      apm: [...prev.apm, user.apm].slice(-HISTORY_LENGTH),
      total_clicks: [...prev.total_clicks, user.total_clicks].slice(-HISTORY_LENGTH),
      active_screen_time: [...prev.active_screen_time, user.active_screen_time].slice(-HISTORY_LENGTH),
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.points, user.apm, user.total_clicks, user.active_screen_time]);

  const metricLabel = METRICS.find((m) => m.key === metric)?.label || metric;

  return (
    <motion.main
      className="max-w-5xl mx-auto px-4 py-6 space-y-6"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <div className="bg-black text-yellow-400 rounded-2xl p-5 shadow-lg space-y-4">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <p className="text-sm opacity-80">Welcome back,</p>
            <p className="text-2xl font-extrabold">{user.username} 😊</p>
          </div>
          <div className="flex gap-6 text-center">
            <Stat label="Points" value={user.points} history={history.points} />
            <Stat label="APM" value={user.apm} decimals={1} history={history.apm} />
            <Stat label="Clicks" value={user.total_clicks} history={history.total_clicks} />
            <Stat
              label="Active Min"
              value={user.active_screen_time}
              decimals={1}
              history={history.active_screen_time}
            />
          </div>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        {METRICS.map((m) => (
          <button
            key={m.key}
            onClick={() => setMetric(m.key)}
            className={`px-4 py-2 rounded-full font-bold border-2 border-black transition ${
              metric === m.key ? "bg-black text-yellow-400" : "bg-white text-black hover:bg-yellow-200"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6 items-start">
        <Leaderboard
          metric={metric}
          metricLabel={metricLabel}
          entries={entries}
          loading={loading}
        />
        <VisibilitySettings user={user} setUser={setUser} onToast={onToast} />
      </div>
    </motion.main>
  );
}

function Stat({ label, value, decimals = 0, history = [] }) {
  return (
    <div className="w-20">
      <p className="text-xs uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-xl font-extrabold tabular-nums">
        <AnimatedNumber value={value} decimals={decimals} />
      </p>
      <Sparkline data={history} color="#facc15" height={20} />
    </div>
  );
}
