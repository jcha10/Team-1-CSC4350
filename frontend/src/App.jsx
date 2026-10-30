import { useEffect, useState, useCallback } from "react";
import { api, session, UNAUTHORIZED_EVENT } from "./api";
import Login from "./components/Login";
import Header from "./components/Header";
import SmileMode from "./components/SmileMode";
import ToastStack from "./components/Toast";

/**
 * Top-level state owner.
 *
 * `user` is the source of truth for identity/role, always populated from
 * a server response (login or /api/me) - never something the UI
 * constructs itself.
 */
export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toasts, setToasts] = useState([]);
  const [demoMode, setDemoMode] = useState(false);

  /**
   * Add a toast message to the stack. The toast will automatically disappear after 3.5 seconds.
   */

  const addToast = useCallback((message, type = "info") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  /**
   * On mount, check if the user is already logged in (via a session token) and fetch their details. If not logged in, we can skip the API call and just set loading to false. We also check if the app is in demo mode.
   */

  useEffect(() => {
    api
      .health()
      .then((h) => setDemoMode(!!h.demo_mode))
      .catch(() => {});

    if (!session.get()) {
      setLoading(false);
      return;
    }
     /**
     * If a session token exists, we attempt to fetch the user's details. If the token is invalid or expired, we clear the session and set loading to false.
     */
    api
      .getMe()
      .then(setUser)
      .catch(() => session.clear())
      .finally(() => setLoading(false));
  }, []);

  // Any 401 mid-session (token expired, revoked by logout elsewhere or a
  // password reset) drops back to the login screen instead of leaving a
  // dashboard that silently stops updating.

  /**
   * Listen for the UNAUTHORIZED_EVENT, which is dispatched when the server responds with a 401 status code. When this event is caught, we clear the session and set the user to null, effectively logging them out and prompting them to log in again.
   */
  useEffect(() => {
    function onUnauthorized() {
      if (!session.get()) return;
      session.clear();
      setUser(null);
      addToast("Your session expired. Please sign in again.", "error");
    }
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, [addToast]);

  /**
   * Handle user login by setting the session token and updating the user state. This function is called when the Login component successfully authenticates a user.
   */

  function handleLogin(token, loggedInUser) {
    session.set(token);
    setUser(loggedInUser);
  }

  /**
   * Handle user logout by calling the API to revoke the session on the server, clearing the session locally, and setting the user state to null. This function is called when the user clicks the logout button in the Header component.
   */
  async function handleLogout() {
    await api.logout().catch(() => {}); // revoke server-side; clear locally regardless
    session.clear();
    setUser(null);
  }

    /**
   * Render the appropriate UI based on the current state. If loading, show a loading indicator. If not logged in, show the Login component. If logged in, show the Header and main content with user details.
   */
  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">Loading…</div>;
  }

  /**
   * If the user is not logged in, render the Login component and the ToastStack for displaying toast messages. The Login component receives the handleLogin function and addToast function as props, along with the demoMode state to indicate if the app is in demo mode.
   */
  if (!user) {
    return (
      <>
        <Login onLogin={handleLogin} onToast={addToast} demoMode={demoMode} />
        <ToastStack toasts={toasts} />
      </>
    );
  }

 /**
   * If the user is logged in, render the Header component with the user details and logout handler, along with the main content displaying a welcome message and user role. The ToastStack is also rendered to display any toast messages.
   */
  return (
    <div className="min-h-screen bg-yellow-50">
      <Header user={user} onLogout={handleLogout} />
      <main className="max-w-5xl mx-auto px-4 py-10">
        <div className="bg-black text-yellow-400 rounded-2xl p-6 shadow-lg">
          <p className="text-sm opacity-80">Welcome,</p>
          <p className="text-2xl font-extrabold">{user.username} 😊</p>
          <p className="text-sm opacity-80 mt-2">
            Signed in as {user.role === "hr_admin" ? "HR Admin" : "Employee"}.
          </p>
        </div>
      </main>
      <ToastStack toasts={toasts} />
    </div>
  );
}
