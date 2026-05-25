import { Agent, run } from "@openai/agents";
import {
  GatewayEvent,
  MemoryRecord,
  SendMessageResponse,
  SessionRecord,
  makeGatewayEvent
} from "@hso/shared";
import { GatewayStore, GatewayStoreOptions } from "@hso/storage";

export type RuntimeOptions = GatewayStoreOptions & {
  store?: GatewayStore;
  runner?: HSOAgentRunner;
};

export type RunContext = {
  session: SessionRecord;
  content: string;
  memory: MemoryRecord[];
};

export interface HSOAgentRunner {
  run(input: string, context: RunContext): Promise<string>;
}

export class OpenAIAgentsRunner implements HSOAgentRunner {
  private readonly model: string;
  private agent: Agent | null = null;

  /** Configures the OpenAI Agents SDK runner without creating network clients yet. */
  constructor(model = process.env.OPENAI_MODEL ?? "gpt-5.4-mini") {
    this.model = model;
  }

  /** Runs one prompt through the HSO agent and normalizes the final output. */
  async run(input: string, context: RunContext): Promise<string> {
    const result = await run(this.getAgent(), this.promptFor(input, context));
    const output = result.finalOutput;
    return typeof output === "string" ? output : JSON.stringify(output);
  }

  /** Lazily constructs the OpenAI agent so tests can inject fake runners. */
  private getAgent(): Agent {
    if (this.agent === null) {
      this.agent = new Agent({
        name: "hso-gateway",
        instructions:
          "You are the HSO local research gateway agent. Respond concisely, summarize the operator task, and avoid inventing manuscript or literature facts.",
        model: this.model
      });
    }
    return this.agent;
  }

  /** Builds the compact agent prompt from session metadata and recent memory. */
  private promptFor(input: string, context: RunContext): string {
    const recentMemory = context.memory
      .slice(-6)
      .map((record) => `${record.role}: ${record.content}`)
      .join("\n");
    return [
      `Session: ${context.session.title} (${context.session.id})`,
      recentMemory ? `Recent memory:\n${recentMemory}` : "Recent memory: none",
      `User message:\n${input}`
    ].join("\n\n");
  }
}

export class GatewayRuntime {
  private readonly store: GatewayStore;
  private readonly runner: HSOAgentRunner;

  /** Wires storage and runner dependencies for route handlers or tests. */
  constructor(options: RuntimeOptions = {}) {
    this.store = options.store ?? new GatewayStore(options);
    this.runner = options.runner ?? new OpenAIAgentsRunner();
  }

  /** Creates a persisted gateway session. */
  createSession(title = "Untitled session"): SessionRecord {
    return this.store.createSession(title);
  }

  /** Lists persisted sessions. */
  listSessions(): SessionRecord[] {
    return this.store.listSessions();
  }

  /** Reads one session by id. */
  getSession(sessionId: string): SessionRecord {
    return this.store.getSession(sessionId);
  }

  /** Reads persisted events for a session. */
  listEvents(sessionId: string): GatewayEvent[] {
    return this.store.listEvents(sessionId);
  }

  /** Reads persisted memory for a session. */
  listMemory(sessionId: string): MemoryRecord[] {
    this.store.getSession(sessionId);
    return this.store.listMemory(sessionId);
  }

  /** Processes one user turn, persisting memory and success or failure events. */
  async processMessage(sessionId: string, content: string): Promise<SendMessageResponse> {
    const normalized = content.trim();
    if (!normalized) {
      throw new Error("Message content cannot be empty.");
    }
    const session = this.store.getSession(sessionId);
    this.store.appendMemory({ session_id: session.id, role: "user", content: normalized });
    const received = makeGatewayEvent({
      session_id: session.id,
      type: "message.received",
      message: "Gateway received a user message."
    });
    const started = makeGatewayEvent({
      session_id: session.id,
      type: "agent.started",
      message: "OpenAI Agents SDK runner accepted the task.",
      agent_name: "hso-gateway",
      payload: { model: process.env.OPENAI_MODEL ?? "gpt-5.4-mini" }
    });
    try {
      const finalOutput = await this.runner.run(normalized, {
        session,
        content: normalized,
        memory: this.store.listMemory(session.id)
      });
      const completed = makeGatewayEvent({
        session_id: session.id,
        type: "agent.completed",
        message: finalOutput || "Agent completed without text output.",
        agent_name: "hso-gateway"
      });
      const events = [received, started, completed];
      this.store.saveEvents(events);
      this.store.appendMemory({
        session_id: session.id,
        role: "assistant",
        content: completed.message,
        metadata: { event_count: events.length }
      });
      return { session, events };
    } catch (error) {
      const failed = makeGatewayEvent({
        session_id: session.id,
        type: "agent.failed",
        message: error instanceof Error ? error.message : String(error),
        agent_name: "hso-gateway"
      });
      const events = [received, started, failed];
      this.store.saveEvents(events);
      this.store.appendMemory({
        session_id: session.id,
        role: "assistant",
        content: failed.message,
        metadata: { event_count: events.length, failed: true }
      });
      throw error;
    }
  }

  /** Closes underlying storage resources. */
  close(): void {
    this.store.close();
  }
}
