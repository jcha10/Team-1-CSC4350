import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import App from "./App";
import { api, session } from "./api";

// From Sprint 2 the signed-in page is Smile Mode. Swap it for a stand-in so
// this test only checks App's own job: login screen or signed-in app.
vi.mock("./components/SmileMode", () => ({ default: () => "Main page" }));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
});

it("skips the login screen when a saved login token is still valid", async () => {
  session.set("saved-token");
  vi.spyOn(api, "health").mockResolvedValue({ status: "ok", demo_mode: false });
  vi.spyOn(api, "getMe").mockResolvedValue({ id: 1, username: "alice", role: "employee" });

  render(<App />);

  // The header only appears once you're signed in.
  expect(await screen.findByText("alice · Employee")).toBeTruthy();
  expect(screen.queryByLabelText("Username")).toBeNull();
  expect(api.getMe).toHaveBeenCalled();
});
