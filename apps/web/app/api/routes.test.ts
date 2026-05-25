import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetGatewayRuntimeForTests } from "../lib/gateway";
import { GET as health } from "./health/route";
import { POST as chat } from "./chat/route";
import { GET as listSessions, POST as createSession } from "./sessions/route";
import { GET as listEvents } from "./sessions/[sessionId]/events/route";
import { GET as listMemory } from "./sessions/[sessionId]/memory/route";
import { POST as sendMessage } from "./sessions/[sessionId]/messages/route";

vi.mock("@openai/agents", () => ({
  Agent: class Agent {
    constructor(readonly config: unknown) {}
  },
  run: async () => ({ finalOutput: "mock agent output" })
}));

describe("Next gateway routes", () => {
  beforeEach(() => {
    process.env.HSO_DATA_DIR = mkdtempSync(path.join(tmpdir(), "hso-route-"));
    resetGatewayRuntimeForTests();
  });

  afterEach(() => {
    resetGatewayRuntimeForTests();
    delete process.env.HSO_DATA_DIR;
  });

  it("serves health and session lifecycle endpoints", async () => {
    expect(await (await health()).json()).toMatchObject({ status: "ok" });

    const created = await (
      await createSession(jsonRequest({ title: "Gateway migration" }))
    ).json();
    expect(created.id).toMatch(/^ses_/);

    const sessions = await (await listSessions()).json();
    expect(sessions).toHaveLength(1);

    const sent = await (
      await sendMessage(jsonRequest({ content: "map migration" }), {
        params: Promise.resolve({ sessionId: created.id })
      })
    ).json();
    expect(sent.events.at(-1)?.message).toBe("mock agent output");

    const events = await (
      await listEvents(new Request("http://test"), {
        params: Promise.resolve({ sessionId: created.id })
      })
    ).json();
    const memory = await (
      await listMemory(new Request("http://test"), {
        params: Promise.resolve({ sessionId: created.id })
      })
    ).json();
    expect(events).toHaveLength(3);
    expect(memory).toHaveLength(2);
  });

  it("returns 404 for unknown session routes", async () => {
    const response = await listEvents(new Request("http://test"), {
      params: Promise.resolve({ sessionId: "missing" })
    });

    expect(response.status).toBe(404);
  });

  it("streams chat responses through the AI SDK endpoint", async () => {
    const created = await (
      await createSession(jsonRequest({ title: "Stream test" }))
    ).json();
    const response = await chat(
      jsonRequest({
        sessionId: created.id,
        messages: [
          {
            role: "user",
            parts: [{ type: "text", text: "stream this turn" }]
          }
        ]
      })
    );

    expect(response.status).toBe(200);
    expect(await response.text()).toContain("mock agent output");
  });
});

function jsonRequest(body: unknown): Request {
  return new Request("http://test", {
    method: "POST",
    body: JSON.stringify(body),
    headers: { "content-type": "application/json" }
  });
}
