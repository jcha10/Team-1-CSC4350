import { expect, it } from "vitest";
import { levelForPoints } from "./LevelBar";

it("250 points is level 3, Team Player, 50 points into the level", () => {
  expect(levelForPoints(250)).toEqual({ level: 3, progress: 50, title: "Team Player" });
});

it("a new account starts at level 1, Newcomer", () => {
  expect(levelForPoints(0)).toEqual({ level: 1, progress: 0, title: "Newcomer" });
});
