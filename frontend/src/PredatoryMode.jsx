import { Fragment, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api";
import useLiveSocket from "../useLiveSocket";
import DisloyaltyChart from "./DisloyaltyChart";
import ActivityFeed from "./ActivityFeed";
import KpiTiles from "./KpiTiles";
import ViolationsTimeline from "./ViolationsTimeline";

/**
 * Predatory Mode (HR dashboard).
 *
 * Every fetch here hits an hr_admin-only backend route. If the caller
 * isn't actually hr_admin, each of these calls independently 403s - this
 * component does not assume the mode switch in Header.jsx was itself a
 * security boundary. On the first 403 we bail out via onDenied(), which
 * flips App.jsx back to Smile Mode.
 */
export default function PredatoryMode({ onToast, onDenied }) {
  const [stats, setStats] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [events, setEvents] = useState([]);
  const [slackConfigured, setSlackConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expandedUser, setExpandedUser] = useState(null);
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [activityByUser, setActivityByUser] = useState({}); // username -> full log (or "loading")
  const deniedRef = useRef(false);

  function handleForbidden(err) {
    if (err.status === 403 && !deniedRef.current) {
      deniedRef.current = true;
      onToast("Access denied: this account is not hr_admin.", "error");
      onDenied();
    }
  }

  async function loadAll() {
    try {
      const [statsData, employeesData, telemetryData, integrations] = await Promise.all([
        api.getDisloyaltyStats(),
        api.getHrEmployees(),
        api.getHrTelemetry(30),
        api.getIntegrationsStatus(),
      ]);
      setStats(statsData);
      setEmployees(employeesData);
      setEvents(telemetryData.map((t) => ({ ...t })).reverse());
      setSlackConfigured(integrations.slack_configured);
    } catch (err) {
      handleForbidden(err);
    } finally {
      setLoading(false);
    }
  }

  // One simulator tick produces an event per employee in a burst; refresh
  // the aggregates once after the burst settles instead of once per event.
  const refreshTimer = useRef(null);

  useEffect(() => {
    loadAll();
    return () => clearTimeout(refreshTimer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function scheduleAggregateRefresh() {
    clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(() => {
      api.getDisloyaltyStats().then(setStats).catch(handleForbidden);
      api.getHrEmployees().then(setEmployees).catch(handleForbidden);
    }, 300);
  }

  useLiveSocket(api.hrFeedSocketUrl, {
    onMessage: (data) => {
      if (data.type !== "activity") return;
      setEvents((prev) => [...prev.slice(-99), data]);
      scheduleAggregateRefresh();
    },
    onReconnect: loadAll,
    onUnauthorized: () => handleForbidden({ status: 403 }),
  });

  function toggleRow(username) {
    const opening = expandedUser !== username;
    setExpandedUser(opening ? username : null);
    if (opening && !activityByUser[username]) {
      setActivityByUser((prev) => ({ ...prev, [username]: "loading" }));
      api
        .getEmployeeActivity(username)
        .then((logs) => setActivityByUser((prev) => ({ ...prev, [username]: logs })))
        .catch((err) => {
          handleForbidden(err);
          setActivityByUser((prev) => ({ ...prev, [username]: [] }));
        });
    }
  }

  const visibleEmployees = flaggedOnly ? employees.filter((e) => e.is_disloyal) : employees;

  if (loading) {
    return <p className="text-gray-400 text-center py-10">Loading HR telemetry…</p>;
  }

  return (
    <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      <div className="bg-red-950/40 border border-red-800 rounded-2xl p-4 text-red-300 text-sm flex items-center justify-between flex-wrap gap-3">
        <span>
          This view shows complete telemetry for every employee, independent of their public
          leaderboard visibility settings. Access is restricted to hr_admin accounts and is enforced
          server-side.
        </span>
        <span
          className={`shrink-0 flex items-center gap-2 rounded-full px-3 py-1 text-xs font-bold border ${
            slackConfigured
              ? "bg-green-950/60 border-green-700 text-green-300"
              : "bg-gray-800/60 border-gray-600 text-gray-400"
          }`}
          title={
            slackConfigured
              ? "Violation alerts are being posted to a real Slack webhook."
              : "No SLACK_WEBHOOK_URL configured - violation alerts are logged server-side instead."
          }
        >
          {slackConfigured ? (
            <motion.span
              className="w-2 h-2 rounded-full bg-green-400"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            />
          ) : (
            <span className="w-2 h-2 rounded-full bg-gray-500" />
          )}
          Slack Alerts: {slackConfigured ? "Connected" : "Not Configured"}
        </span>
      </div>

      <KpiTiles employees={employees} events={events} />

      <div className="grid lg:grid-cols-2 gap-6">
        <DisloyaltyChart stats={stats} />
        <ActivityFeed events={events} />
      </div>

      <ViolationsTimeline events={events} />

      <div className="bg-gray-900 border border-red-900/50 rounded-2xl p-5 shadow-lg overflow-x-auto">
        <div className="flex items-center justify-between flex-wrap gap-2 mb-1">
          <h2 className="text-lg font-bold text-red-400">Personnel Telemetry</h2>
          <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={flaggedOnly}
              onChange={(e) => setFlaggedOnly(e.target.checked)}
              className="w-4 h-4 accent-red-600"
            />
            Show flagged only
          </label>
        </div>
        <p className="text-xs text-gray-500 mb-3">Click a row to pull that person's full activity log.</p>
        <table className="w-full text-sm text-left text-gray-300">
          <thead className="text-gray-500 uppercase text-xs">
            <tr>
              <th className="py-2 pr-4">User</th>
              <th className="py-2 pr-4">Points</th>
              <th className="py-2 pr-4">APM</th>
              <th className="py-2 pr-4">Clicks</th>
              <th className="py-2 pr-4">Active Min</th>
              <th className="py-2 pr-4">Violations</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Hidden from Peers</th>
            </tr>
          </thead>
          <tbody>
            {visibleEmployees.length === 0 && (
              <tr>
                <td colSpan={8} className="py-4 text-center text-gray-500 text-xs">
                  No flagged personnel.
                </td>
              </tr>
            )}
            {visibleEmployees.map((e) => {
              const isExpanded = expandedUser === e.username;
              const activity = activityByUser[e.username];
              return (
                <Fragment key={e.id}>
                  <tr
                    onClick={() => toggleRow(e.username)}
                    className="border-t border-gray-800 cursor-pointer hover:bg-gray-800/60 transition"
                  >
                    <td className="py-2 pr-4 font-semibold text-gray-100">
                      {e.username}
                      {e.role === "hr_admin" && (
                        <span className="ml-2 text-[10px] uppercase tracking-wide text-amber-400/80">admin</span>
                      )}
                    </td>
                    <td className="py-2 pr-4">{e.points}</td>
                    <td className="py-2 pr-4">{e.apm}</td>
                    <td className="py-2 pr-4">{e.total_clicks}</td>
                    <td className="py-2 pr-4">{e.active_screen_time}</td>
                    <td className="py-2 pr-4">{e.disloyal_violation_count}</td>
                    <td className="py-2 pr-4">
                      {e.is_disloyal ? (
                        <span className="bg-red-600 text-white px-2 py-0.5 rounded text-xs font-bold">
                          FLAGGED
                        </span>
                      ) : (
                        <span className="text-gray-500 text-xs">clean</span>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-400">
                      {e.hidden_metrics.length ? e.hidden_metrics.join(", ") : "—"}
                    </td>
                  </tr>
                  <AnimatePresence>
                    {isExpanded && (
                      <tr>
                        <td colSpan={8} className="p-0 border-t border-gray-800">
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.15 }}
                            className="bg-black/30"
                          >
                            <div className="px-4 py-3 font-mono text-xs">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-gray-400 uppercase tracking-wide">
                                  Full activity log — {e.username}
                                </span>
                                {Array.isArray(activity) && (
                                  <span className="text-gray-500">
                                    {activity.filter((a) => a.is_flagged).length} flagged / {activity.length} total
                                  </span>
                                )}
                              </div>
                              {activity === "loading" || activity === undefined ? (
                                <p className="text-gray-500">Loading…</p>
                              ) : activity.length === 0 ? (
                                <p className="text-gray-500">No activity captured yet.</p>
                              ) : (
                                <div className="space-y-1 max-h-72 overflow-y-auto pr-1">
                                  {activity.map((ev) => (
                                    <p
                                      key={ev.id}
                                      className={`break-words ${ev.is_flagged ? "text-red-300" : "text-gray-400"}`}
                                    >
                                      {new Date(ev.timestamp).toLocaleString()} — {ev.raw_text}
                                      {ev.is_flagged && (
                                        <span className="ml-2 uppercase text-[10px] bg-red-600 text-white px-1.5 py-0.5 rounded">
                                          {ev.matched_keyword}
                                        </span>
                                      )}
                                    </p>
                                  ))}
                                </div>
                              )}
                            </div>
                          </motion.div>
                        </td>
                      </tr>
                    )}
                  </AnimatePresence>
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </main>
  );
}
