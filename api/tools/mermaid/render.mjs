#!/usr/bin/env node
/**
 * Render Mermaid source (stdin or argv file) to PNG on stdout.
 *
 * Mermaid's default SVG uses <foreignObject> HTML labels. WeasyPrint and
 * CairoSVG do not paint those, so exported diagrams show empty boxes.
 * Chromium PNG keeps CJK text intact.
 */
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { run } from "@mermaid-js/mermaid-cli";

async function readSource() {
  if (process.argv[2] && process.argv[2] !== "-") {
    return readFileSync(process.argv[2], "utf8");
  }
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf8");
}

const source = (await readSource()).trim();
if (!source) {
  console.error("empty mermaid source");
  process.exit(2);
}

const dir = mkdtempSync(join(tmpdir(), "mmd-"));
const inFile = join(dir, "diagram.mmd");
const outFile = join(dir, "diagram.png");

try {
  writeFileSync(inFile, source, "utf8");

  const executablePath = process.env.PUPPETEER_EXECUTABLE_PATH || "";
  const puppeteerConfig = {
    headless: "shell",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
  };
  if (executablePath) {
    puppeteerConfig.executablePath = executablePath;
  }

  await run(inFile, outFile, {
    outputFormat: "png",
    quiet: true,
    puppeteerConfig,
    parseMMDOptions: {
      mermaidConfig: {
        theme: "neutral",
        securityLevel: "loose",
        htmlLabels: false,
        fontFamily:
          '"Noto Sans CJK JP", "Noto Sans CJK", "Noto Sans JP", sans-serif',
        fontSize: 13,
        flowchart: {
          htmlLabels: false,
          useMaxWidth: true,
          nodeSpacing: 18,
          rankSpacing: 28,
          padding: 6,
          diagramPadding: 8,
        },
        themeVariables: {
          fontSize: "13px",
        },
      },
      backgroundColor: "white",
      // Keep canvas modest so TD flowcharts don't become poster-sized.
      viewport: { width: 720, height: 900, deviceScaleFactor: 1.5 },
    },
  });

  process.stdout.write(readFileSync(outFile));
} finally {
  try {
    rmSync(dir, { recursive: true, force: true });
  } catch {
    /* ignore */
  }
}
