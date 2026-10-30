import { afterEach, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import Leaderboard from "./Leaderboard";

afterEach(cleanup);

const entries = [
  { username: "bob", value: 30, is_you: false },
  { username: "alice", value: 20, is_you: true },
  { username: "carol", value: 10, is_you: false },
];

it("shows your rank and the visible peer average", () => {
  render(<Leaderboard metric="points" metricLabel="Points" entries={entries} loading={false} />);

  expect(screen.getByText(/Your rank: #2/)).toBeTruthy();
  expect(screen.getByText(/Visible peer avg/)).toBeTruthy();
  expect(screen.getByText("20.0")).toBeTruthy(); // (30 + 20 + 10) / 3
});
