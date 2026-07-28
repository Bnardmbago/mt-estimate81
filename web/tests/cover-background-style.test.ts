import assert from "node:assert/strict";
import { test } from "node:test";
import {
  coverBackgroundImageStyle,
  coverBackgroundInlineCss,
} from "../lib/cover-background-style";

test("cover background horizontal position changes left and translate anchor", () => {
  const left = coverBackgroundImageStyle({ x: 15, y: 50, zoom: 1, fit: "cover" });
  const right = coverBackgroundImageStyle({ x: 85, y: 50, zoom: 1, fit: "cover" });

  assert.equal(left.left, "15%");
  assert.equal(left.transform, "translate(-15%, -50%)");
  assert.equal(right.left, "85%");
  assert.equal(right.transform, "translate(-85%, -50%)");
  assert.notEqual(left.left, right.left);
});

test("cover background zoom grows min size so both axes can pan", () => {
  const style = coverBackgroundImageStyle({ x: 20, y: 80, zoom: 1.5, fit: "cover" });

  assert.equal(style.minWidth, "150%");
  assert.equal(style.minHeight, "150%");
  assert.equal(style.maxWidth, "none");
  assert.equal(style.left, "20%");
  assert.equal(style.top, "80%");
  assert.equal(style.transform, "translate(-20%, -80%)");
});

test("contain and fill fits keep horizontal anchoring", () => {
  const contain = coverBackgroundImageStyle({ x: 10, y: 90, zoom: 2, fit: "contain" });
  assert.equal(contain.left, "10%");
  assert.equal(contain.maxWidth, "200%");
  assert.equal(contain.maxHeight, "200%");
  assert.equal(contain.transform, "translate(-10%, -90%)");

  const fill = coverBackgroundImageStyle({ x: 0, y: 100, zoom: 1.25, fit: "fill" });
  assert.equal(fill.left, "0%");
  assert.equal(fill.width, "125%");
  assert.equal(fill.height, "125%");
  assert.equal(fill.transform, "translate(0%, -100%)");
});

test("inline CSS mirrors style helper for export templates", () => {
  const css = coverBackgroundInlineCss({ x: 30, y: 70, zoom: 1.2, fit: "cover", opacity: 0.8 });
  assert.match(css, /left:30%/);
  assert.match(css, /top:70%/);
  assert.match(css, /transform:translate\(-30%, -70%\)/);
  assert.match(css, /min-width:120%/);
  assert.match(css, /min-height:120%/);
  assert.match(css, /opacity:0\.8/);
});
