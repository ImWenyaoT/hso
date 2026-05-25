import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { GatewayRuntime, HSOAgentRunner, RunContext } from "./index.js";

class FakeRunner implements HSOAgentRunner {
  async run(input: string, context: RunContext): Promise<string> {
    return `handled ${input} for ${context.session.title}`;
  }
}

class FailingRunner implements HSOAgentRunner {
  async run(): Promise<string> {
    throw new Error("agent exploded");
  }
}

function dataDir(): string {
  return mkdtempSync(path.join(tmpdir(), "hso-runtime-"));
}

describe("GatewayRuntime", () => {
  it("records a successful agent turn with events and memory", async () => {
    const runtime = new GatewayRuntime({ dataDir: dataDir(), runner: new FakeRunner() });
    const session = runtime.createSession("Gateway migration");

    const response = await runtime.processMessage(session.id, "map migration");

    expect(response.events.map((event) => event.type)).toEqual([
      "message.received",
      "agent.started",
      "agent.completed"
    ]);
    expect(runtime.listEvents(session.id)).toHaveLength(3);
    expect(runtime.listMemory(session.id).map((record) => record.role)).toEqual([
      "user",
      "assistant"
    ]);
    runtime.close();
  });

  it("rejects empty input before invoking the agent", async () => {
    const runtime = new GatewayRuntime({ dataDir: dataDir(), runner: new FakeRunner() });
    const session = runtime.createSession("Gateway migration");

    await expect(runtime.processMessage(session.id, "   ")).rejects.toThrow("empty");

    runtime.close();
  });

  it("persists a failed event when the agent runner throws", async () => {
    const runtime = new GatewayRuntime({ dataDir: dataDir(), runner: new FailingRunner() });
    const session = runtime.createSession("Gateway migration");

    await expect(runtime.processMessage(session.id, "fail")).rejects.toThrow("agent exploded");

    expect(runtime.listEvents(session.id).at(-1)?.type).toBe("agent.failed");
    expect(runtime.listMemory(session.id).at(-1)?.metadata).toMatchObject({ failed: true });
    runtime.close();
  });
});
