#!/usr/bin/env node
import { existsSync, readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import path from "node:path";

import { GatewayRuntime } from "@hso/agent-runtime";

type Command = "start" | "status" | "smoke" | "help";

/** Dispatches the minimal TypeScript hso CLI commands. */
async function main(argv: string[]): Promise<void> {
  loadDotenv();
  const command = (argv[2] ?? "help") as Command;
  if (command === "start") {
    startNext();
    return;
  }
  if (command === "status") {
    await status(argv[3] ?? "http://127.0.0.1:3000/api/health");
    return;
  }
  if (command === "smoke") {
    await smoke(argv.slice(3).join(" ") || "Reply with exactly: hso-ok");
    return;
  }
  help();
}

/** Starts the Next.js app that owns both UI and gateway route handlers. */
function startNext(): void {
  const child = spawn("npm", ["--workspace", "hso-web", "run", "dev"], {
    cwd: findWorkspaceRoot(),
    env: process.env,
    stdio: "inherit"
  });
  child.on("exit", (code) => {
    process.exit(code ?? 0);
  });
}

/** Fetches the gateway health endpoint and prints the JSON body. */
async function status(url: string): Promise<void> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Gateway status failed: ${response.status}`);
  }
  console.log(await response.text());
}

/** Runs one real OpenAI Agents SDK turn and prints a compact smoke result. */
async function smoke(message: string): Promise<void> {
  if (!process.env.OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY is required for `hso smoke`.");
  }
  const runtime = new GatewayRuntime();
  const session = runtime.createSession("TS smoke");
  const response = await runtime.processMessage(session.id, message);
  console.log(
    JSON.stringify(
      {
        session_id: response.session.id,
        event_count: response.events.length,
        final: response.events.at(-1)?.message ?? ""
      },
      null,
      2
    )
  );
  runtime.close();
}

/** Prints CLI usage. */
function help(): void {
  console.log(`hso TypeScript gateway

Commands:
  hso start           Start the Next.js full-stack gateway
  hso status [url]    Check /api/health
  hso smoke [prompt]  Run one real OpenAI Agents SDK turn and persist it
`);
}

/** Loads root .env values without logging secrets. */
function loadDotenv(): void {
  const file = path.join(findWorkspaceRoot(), ".env");
  if (!existsSync(file)) {
    return;
  }
  for (const line of readFileSync(file, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) {
      continue;
    }
    const [key, ...rest] = trimmed.split("=");
    process.env[key] ??= rest.join("=").replace(/^["']|["']$/g, "");
  }
}

/** Walks upward to find the npm workspace root. */
function findWorkspaceRoot(start = process.cwd()): string {
  let current = path.resolve(start);
  for (;;) {
    if (existsSync(path.join(current, "package.json")) && existsSync(path.join(current, "apps"))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      return path.resolve(start);
    }
    current = parent;
  }
}

main(process.argv).catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
