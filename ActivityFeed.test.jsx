import { afterEach, expect, it } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ActivityFeed from "./ActivityFeed";

afterEach(cleanup);

const events = [
  {
    timestamp: "2026-10-01T10:00:00",
    username: "alice",
    raw_text: "Opened Steam store page",
    matched_keyword: "steam",
    is_flagged: true,
  },
  {
    timestamp: "2026-10-01T10:00:01",
    username: "bob",
    raw_text: "Joined Zoom standup",
    matched_keyword: null,
    is_flagged: false,
  },
];

it("the search box and the flagged-only box narrow the feed", async () => {
  render(<ActivityFeed events={events} />);
  const search = screen.getByPlaceholderText("Filter by user or keyword…");

  // Searching for "bob" hides alice's event.
  await userEvent.type(search, "bob");
  await waitFor(() => expect(screen.queryByText(/Opened Steam store page/)).toBeNull());
  expect(screen.getByText(/Joined Zoom standup/)).toBeTruthy();

  // Clearing the search and ticking "Flagged only" shows just the flagged event.
  await userEvent.clear(search);
  await userEvent.click(screen.getByLabelText("Flagged only"));
  await waitFor(() => expect(screen.queryByText(/Joined Zoom standup/)).toBeNull());
  expect(screen.getByText(/Opened Steam store page/)).toBeTruthy();
});
