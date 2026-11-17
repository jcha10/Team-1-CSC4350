import { useEffect, useRef } from "react";
import { motion } from "framer-motion";

export const BADGE_DEFS = [
  { key: "century", icon: "🌟", label: "Century Club", desc: "Reach 100 points", test: (u) => u.points >= 100 },
  { key: "speed", icon: "⚡", label: "Speed Demon", desc: "Hit 30+ APM", test: (u) => u.apm >= 30 },
  { key: "clicks", icon: "🖱️", label: "Click Master", desc: "300+ total clicks", test: (u) => u.total_clicks >= 300 },
  {
    key: "marathon",
    icon: "⏱️",
    label: "Marathoner",
    desc: "15+ active minutes",
    test: (u) => u.active_screen_time >= 15,
  },
  { key: "streak", icon: "🔥", label: "On Fire", desc: "3+ day login streak", test: (u) => u.current_streak >= 3 },
  { key: "fan", icon: "🙌", label: "Fan Favorite", desc: "Receive 3+ kudos", test: (u) => u.kudos_received >= 3 },
  { key: "overachiever", icon: "💯", label: "Overachiever", desc: "Reach 500 points", test: (u) => u.points >= 500 },
];

/**
 * Renders the badge grid and fires onUnlock(badge) the first time each
 * badge's condition flips from false to true, so App.jsx can toast it.
 * Unlock state itself isn't persisted anywhere - it's just re-derived
 * from the current `user` stats on every render, so a badge that's
 * "earned" stays earned as long as the underlying stat does.
 */
export default function Badges({ user, onUnlock }) {
  const prevUnlocked = useRef(new Set());

  useEffect(() => {
    const nowUnlocked = new Set(BADGE_DEFS.filter((b) => b.test(user)).map((b) => b.key));
    for (const key of nowUnlocked) {
      if (!prevUnlocked.current.has(key)) {
        const badge = BADGE_DEFS.find((b) => b.key === key);
        onUnlock?.(badge);
      }
    }
    prevUnlocked.current = nowUnlocked;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.points, user.apm, user.total_clicks, user.active_screen_time, user.current_streak, user.kudos_received]);

  return (
    <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
      {BADGE_DEFS.map((b, i) => {
        const unlocked = b.test(user);
        return (
          <motion.div
            key={b.key}
            title={`${b.label}: ${b.desc}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: i * 0.03 }}
            className={`flex flex-col items-center justify-center rounded-xl border-2 p-2 text-center transition ${
              unlocked ? "bg-yellow-100 border-black" : "bg-gray-100 border-gray-300 opacity-40 grayscale"
            }`}
          >
            <span className="text-xl">{b.icon}</span>
            <span className="text-[10px] font-bold leading-tight mt-1">{b.label}</span>
          </motion.div>
        );
      })}
    </div>
  );
}
