import { afterEach, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import KpiTiles from "./KpiTiles";

afterEach(cleanup);

it("shows the most common flagged keyword", () => {
  const employees = [
    { username: "alice", is_disloyal: true, disloyal_violation_count: 2 },
    { username: "bob", is_disloyal: false, disloyal_violation_count: 0 },
  ];
  const events = [
    { is_flagged: true, matched_keyword: "steam" },
    { is_flagged: true, matched_keyword: "resume" },
    { is_flagged: true, matched_keyword: "steam" },
    { is_flagged: false, matched_keyword: null },
  ];

  render(<KpiTiles employees={employees} events={events} />);

  expect(screen.getByText("Top Restricted Keyword")).toBeTruthy();
  expect(screen.getByText("steam")).toBeTruthy();
});
