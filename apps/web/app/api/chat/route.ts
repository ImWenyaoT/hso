import { createUIMessageStream, createUIMessageStreamResponse } from "ai";

import { getGatewayRuntime } from "../../lib/gateway";

export const runtime = "nodejs";

type ChatRequest = {
  messages?: Array<{
    role?: string;
    content?: string;
    parts?: Array<{ type?: string; text?: string }>;
  }>;
  sessionId?: string;
};

/** Streams an AI SDK UIMessage response while GatewayRuntime owns orchestration. */
export async function POST(request: Request): Promise<Response> {
  const body = (await request.json().catch(() => ({}))) as ChatRequest;
  const prompt = lastUserText(body.messages ?? []);
  const stream = createUIMessageStream({
    async execute({ writer }) {
      const textId = "hso-agent-output";
      writer.write({ type: "text-start", id: textId });
      try {
        const runtime = getGatewayRuntime();
        const sessionId = body.sessionId ?? runtime.createSession("UI chat").id;
        const result = await runtime.processMessage(sessionId, prompt || "Run the HSO gateway.");
        const finalText = result.events.at(-1)?.message ?? "";
        writer.write({ type: "text-delta", id: textId, delta: finalText });
        writer.write({
          type: "data-message",
          data: { sessionId: result.session.id, events: result.events }
        });
      } catch (error) {
        writer.write({
          type: "text-delta",
          id: textId,
          delta: error instanceof Error ? error.message : String(error)
        });
      } finally {
        writer.write({ type: "text-end", id: textId });
      }
    }
  });
  return createUIMessageStreamResponse({ stream });
}

/** Extracts the newest user text from the Vercel AI SDK UIMessage request body. */
function lastUserText(messages: NonNullable<ChatRequest["messages"]>): string {
  const message = [...messages].reverse().find((item) => item.role === "user");
  if (!message) {
    return "";
  }
  if (typeof message.content === "string") {
    return message.content;
  }
  return (
    message.parts
      ?.filter((part) => part.type === "text")
      .map((part) => part.text ?? "")
      .join("\n") ?? ""
  );
}
