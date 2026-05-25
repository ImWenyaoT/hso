import { GatewayRuntime } from "@hso/agent-runtime";
import { UnknownSessionError } from "@hso/storage";

let runtime: GatewayRuntime | null = null;

/** Lazily creates the gateway runtime so builds do not open SQLite or read model env. */
export function getGatewayRuntime(): GatewayRuntime {
  if (runtime === null) {
    runtime = new GatewayRuntime();
  }
  return runtime;
}

/** Resets the route-handler singleton between tests. */
export function resetGatewayRuntimeForTests(): void {
  runtime?.close();
  runtime = null;
}

/** Returns a JSON response with the same shape as the legacy FastAPI gateway. */
export function jsonResponse(payload: unknown, init?: ResponseInit): Response {
  return Response.json(payload, init);
}

/** Maps known runtime errors to stable HTTP status codes. */
export function errorResponse(error: unknown): Response {
  if (error instanceof UnknownSessionError) {
    return jsonResponse({ detail: error.message }, { status: 404 });
  }
  if (error instanceof Error && error.message.toLowerCase().includes("empty")) {
    return jsonResponse({ detail: error.message }, { status: 400 });
  }
  return jsonResponse(
    { detail: error instanceof Error ? error.message : String(error) },
    { status: 500 }
  );
}

/** Reads the dynamic session id from a Next.js App Router handler context. */
export async function sessionIdFromContext(context: {
  params: Promise<{ sessionId: string }>;
}): Promise<string> {
  return (await context.params).sessionId;
}
