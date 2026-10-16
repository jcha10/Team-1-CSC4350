import { Component } from "react";

/** Last line of defense: a render crash shows a recoverable screen, not a blank page. */
// Catches errors in child components and displays a fallback screen.
export default class ErrorBoundary extends Component {
  // Stores the error; null means no error has been caught.
  state = { error: null };

  // Updates state when a child component throws an error during rendering.
  static getDerivedStateFromError(error) {
    return { error };
  }

  // Logs the error and component stack to help with debugging.
  componentDidCatch(error, info) {
    console.error("Smiley UI crashed:", error, info.componentStack);
  }

  render() {
    // If there is no error, display the child components normally.
    if (!this.state.error) return this.props.children;

    // If an error occurs, display a message and a reload button.
    return (
      <div className="min-h-screen bg-yellow-400 flex items-center justify-center px-4">
        <div className="bg-white border-4 border-black rounded-2xl p-8 max-w-sm text-center">
          {/* Visual indicator that something went wrong. */}
          <div className="text-5xl mb-2">😵</div>

          <h1 className="text-xl font-extrabold mb-2">Something went wrong</h1>
          <p className="text-sm text-gray-600 mb-4">
            The page hit an unexpected error. Reloading usually fixes it.
          </p>

          {/* Reloads the page so the user can try again. */}
          <button
            onClick={() => window.location.reload()}
            className="bg-black text-yellow-400 font-bold rounded-lg px-4 py-2 hover:bg-gray-800"
          >
            Reload
          </button>
        </div>
      </div>
    );
  }
}
