import { METRICS, api } from "../api";

/**
 * Itemized, per-metric visibility controls.
 *
 * This is a transparent PEER-VISIBILITY setting, not a monitoring
 * opt-out. Toggling a metric off does exactly one thing: it removes
 * your username from that metric's public leaderboard, by flipping
 * MetricVisibility.is_public on the backend (PATCH /api/me/visibility).
 * It never touches ActivityLog rows, never clears is_disloyal, and has
 * no effect on what HR can see in Predatory Mode - that monitoring
 * stream is mandatory and runs independently of these switches. The
 * copy below says exactly that, on purpose.
 */
export default function VisibilitySettings({ user, setUser, onToast }) {
  const visMap = Object.fromEntries(user.visibilities.map((v) => [v.metric, v.is_public]));

  async function toggle(metric) {
    const next = !visMap[metric];
    try {
      const updated = await api.updateVisibility(metric, next);
      setUser(updated);
      const label = METRICS.find((m) => m.key === metric)?.label || metric;
      onToast(
        next
          ? `${label} is now visible to peers on the public leaderboard.`
          : `${label} is now hidden from the public leaderboard. Company activity monitoring is unaffected and continues per IT policy.`,
        "info"
      );
    } catch (err) {
      onToast(err.message || "Could not update visibility", "error");
    }
  }

  return (
    <div className="bg-white border-4 border-black rounded-2xl p-5 shadow-lg">
      <h2 className="text-xl font-extrabold text-black mb-1">⚙️ Leaderboard Visibility</h2>
      <p className="text-xs text-gray-600 mb-4 leading-relaxed">
        These switches control only what your coworkers see on the public leaderboard, one metric at a
        time. They do not pause, limit, or disable company activity monitoring — that continues
        regardless of these settings, per IT/security policy.
      </p>
      <div className="space-y-2">
        {METRICS.map((m) => (
          <label
            key={m.key}
            className="flex items-center justify-between px-3 py-2 rounded-lg bg-yellow-50 cursor-pointer"
          >
            <span className="font-semibold text-black">{m.label}</span>
            <span className="flex items-center gap-2 text-sm">
              <span className={visMap[m.key] ? "text-black" : "text-gray-400"}>
                {visMap[m.key] ? "Public" : "Hidden from peers"}
              </span>
              <input
                type="checkbox"
                checked={!!visMap[m.key]}
                onChange={() => toggle(m.key)}
                className="w-5 h-5 accent-black"
              />
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
