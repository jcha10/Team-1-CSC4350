import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "../api";

function timeAgo(iso) {
  const seconds = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/**
 * Company-wide posts. Read access is universal; the composer below only
 * renders for hr_admin sessions - but that's a UI convenience, not the
 * security boundary. POST /api/announcements independently rejects
 * anyone who isn't hr_admin server-side (see require_hr_admin in main.py),
 * same pattern as the rest of this app.
 */
export default function Announcements({ user, onToast }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [posting, setPosting] = useState(false);

  async function load() {
    try {
      setPosts(await api.getAnnouncements());
    } catch (err) {
      onToast(err.message || "Could not load announcements", "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const TITLE_MAX = 200;
  const BODY_MAX = 2000;
  const canPost = title.trim() && body.trim() && !posting;

  async function submit(e) {
    e.preventDefault();
    if (!canPost) return;
    setPosting(true);
    try {
      const post = await api.createAnnouncement(title.trim(), body.trim());
      setPosts((prev) => [post, ...prev]);
      setTitle("");
      setBody("");
      onToast("Announcement posted.", "info");
    } catch (err) {
      onToast(err.message || "Could not post announcement", "error");
    } finally {
      setPosting(false);
    }
  }

  return (
    <div className="bg-white border-4 border-black rounded-2xl p-5 shadow-lg">
      <h2 className="text-xl font-extrabold text-black mb-3">📣 Announcements</h2>

      {user.role === "hr_admin" && (
        <form onSubmit={submit} className="mb-4 space-y-2 bg-yellow-50 rounded-lg p-3">
          <div>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Title"
              aria-label="Announcement title"
              maxLength={TITLE_MAX}
              className="w-full border-2 border-black rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
            />
            <p className="text-[10px] text-gray-500 text-right mt-0.5">
              {title.length}/{TITLE_MAX}
            </p>
          </div>
          <div>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="What's the update?"
              aria-label="Announcement body"
              maxLength={BODY_MAX}
              rows={3}
              className="w-full border-2 border-black rounded-lg px-3 py-1.5 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-yellow-400"
            />
            <p className="text-[10px] text-gray-500 text-right mt-0.5">
              {body.length}/{BODY_MAX}
            </p>
          </div>
          <button
            type="submit"
            disabled={!canPost}
            className="bg-black text-yellow-400 font-bold rounded-lg px-3 py-1.5 text-sm hover:bg-gray-800 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {posting ? "Posting…" : "Post to everyone"}
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : posts.length === 0 ? (
        <p className="text-gray-500 text-sm">No announcements yet.</p>
      ) : (
        <ul className="space-y-2 max-h-64 overflow-y-auto pr-1">
          {posts.map((p, i) => (
            <motion.li
              key={p.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: Math.min(i * 0.03, 0.3) }}
              className="bg-yellow-50 rounded-lg px-3 py-2"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="font-bold text-sm text-black min-w-0 break-words">{p.title}</p>
                <span className="text-[10px] text-gray-500 shrink-0">{timeAgo(p.created_at)}</span>
              </div>
              <p className="text-sm text-gray-700 whitespace-pre-wrap break-words">{p.body}</p>
              <p className="text-[10px] text-gray-500 mt-1 break-words">— {p.author_username}, HR</p>
            </motion.li>
          ))}
        </ul>
      )}
    </div>
  );
}
