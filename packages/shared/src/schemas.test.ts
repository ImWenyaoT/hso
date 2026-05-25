import { describe, expect, it } from "vitest";

import {
  createSessionRequestSchema,
  makeGatewayEvent,
  makeMemoryRecord,
  makeSessionRecord,
  sendMessageRequestSchema
} from "./index.js";

describe("shared gateway schemas", () => {
  it("creates Python-compatible session, event, and memory records", () => {
    const session = makeSessionRecord("Gateway migration");
    const event = makeGatewayEvent({
      session_id: session.id,
      type: "agent.completed",
      message: "done",
      agent_name: "main",
      payload: { count: 1 }
    });
    const memory = makeMemoryRecord({
      session_id: session.id,
      role: "assistant",
      content: "done"
    });

    expect(session.id).toMatch(/^ses_/);
    expect(event.id).toMatch(/^evt_/);
    expect(event.payload).toEqual({ count: 1 });
    expect(memory.id).toMatch(/^mem_/);
  });

  it("normalizes request bodies", () => {
    expect(createSessionRequestSchema.parse({}).title).toBe("Untitled session");
    expect(sendMessageRequestSchema.safeParse({ content: "   " }).success).toBe(false);
  });
});
