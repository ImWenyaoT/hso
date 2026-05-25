import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { makeGatewayEvent } from "@hso/shared";

import { GatewayStore, UnknownSessionError } from "./index.js";

function tempDir(): string {
  return mkdtempSync(path.join(tmpdir(), "hso-store-"));
}

describe("GatewayStore", () => {
  it("persists sessions, events, and memory across store instances", () => {
    const dataDir = tempDir();
    const first = new GatewayStore({ dataDir });
    const session = first.createSession("Gateway migration");
    const event = makeGatewayEvent({
      session_id: session.id,
      type: "agent.completed",
      message: "done",
      agent_name: "main"
    });
    first.saveEvents([event]);
    first.appendMemory({ session_id: session.id, role: "user", content: "hello" });
    first.close();

    const second = new GatewayStore({ dataDir });

    expect(second.listSessions()).toEqual([session]);
    expect(second.listEvents(session.id)).toEqual([event]);
    expect(second.listMemory(session.id)).toHaveLength(1);
    second.close();
  });

  it("raises a typed error for unknown sessions", () => {
    const store = new GatewayStore({ dataDir: tempDir() });

    expect(() => store.getSession("missing")).toThrow(UnknownSessionError);

    store.close();
  });

  it("imports legacy JSONL memory only into an empty store", () => {
    const dataDir = tempDir();
    const legacy = path.join(dataDir, "memory.jsonl");
    writeFileSync(
      legacy,
      JSON.stringify({
        id: "mem_legacy",
        session_id: "ses_1",
        role: "user",
        content: "legacy",
        metadata: {},
        created_at: new Date().toISOString()
      })
    );

    const store = new GatewayStore({ dataDir, legacyJsonlPath: legacy });

    expect(store.listMemory("ses_1")[0]?.content).toBe("legacy");
    store.close();
  });
});
