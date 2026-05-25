import { sendMessageRequestSchema } from "@hso/shared";

import {
  errorResponse,
  getGatewayRuntime,
  jsonResponse,
  sessionIdFromContext
} from "../../../../lib/gateway";

export const runtime = "nodejs";

/** Runs one agent turn for a session and returns the persisted gateway events. */
export async function POST(
  request: Request,
  context: { params: Promise<{ sessionId: string }> }
): Promise<Response> {
  try {
    const sessionId = await sessionIdFromContext(context);
    const body = sendMessageRequestSchema.parse(await request.json());
    return jsonResponse(await getGatewayRuntime().processMessage(sessionId, body.content));
  } catch (error) {
    return errorResponse(error);
  }
}
