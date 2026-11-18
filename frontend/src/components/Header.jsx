import { useRef } from "react";
import { api } from "../api";

const CLICK_WINDOW_MS = 1500;
const CLICKS_REQUIRED = 3;

/**
 * Shared header for both modes. The Smiley logo is the hidden toggle:
 * click it three times within 1.5s and the frontend asks the backend
 * "am I hr_admin?" via GET /api/hr/verify. The backend's answer (not
 * anything cached client-side) decides whether the UI is allowed to
 * switch into Predatory Mode.
 */
export default function Header({ mode, setMode, user, onLogout, onToast }) {
  const clickTimes = useRef([]);

  async function handleLogoClick() {
    const now = Date.now();
    clickTimes.current = [...clickTimes.current, now].filter((t) => now - t < CLICK_WINDOW_MS);

    if (clickTimes.current.length >= CLICKS_REQUIRED) {
      clickTimes.current = [];

      if (mode === "predatory") {
        setMode("smile");
        return;
      }

      const allowed = await api.verifyHrAccess();
      if (allowed) {
        setMode("predatory");
        onToast("Predatory Mode activated.", "info");
      }
      // Non-admin accounts get no visible reaction at all - the toggle
      // stays hidden for them, exactly as intended.
    }
  }

  const dark = mode === "predatory";

  return (
    <header
      className={`sticky top-0 z-40 flex items-center justify-between px-6 py-3 border-b-4 ${
        dark ? "bg-gray-950 border-red-900 text-red-400" : "bg-yellow-400 border-black text-black"
      }`}
    >
      <button
        onClick={handleLogoClick}
        className="flex items-center gap-2 font-extrabold text-lg select-none"
        title="Smiley"
        aria-label="Smiley"
      >
        <span className="text-2xl">{dark ? "🙂" : "😊"}</span>
        <span>{dark ? "SMILEY // PREDATORY MODE" : "Smiley"}</span>
      </button>

      <div className="flex items-center gap-4 text-sm">
        <span className={dark ? "text-gray-400" : "text-black/70"}>
          {user.username} · {user.role === "hr_admin" ? "HR Admin" : "Employee"}
        </span>
        <button
          onClick={onLogout}
          className={`font-semibold rounded-lg px-3 py-1 border-2 ${
            dark
              ? "border-red-900 text-red-400 hover:bg-red-950"
              : "border-black text-black hover:bg-black hover:text-yellow-400"
          } transition`}
        >
          Log out
        </button>
      </div>
    </header>
  );
}
