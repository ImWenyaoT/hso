import { createSessionRequestSchema } from "@hso/shared";

import { errorResponse, getGatewayRuntime, jsonResponse } from "../../lib/gateway";

export const runtime = "nodejs";

/** Lists persisted gateway sessions. */
export async function GET(): Promise<Response> {
  try {
    return jsonResponse(getGatewayRuntime().listSessions());
  } catch (error) {
    return errorResponse(error);
  }
}

/** Creates a new gateway session from a JSON request body. */
export async function POST(request: Request): Promise<Response> {
  try {
    const body = createSessionRequestSchema.parse(await request.json().catch(() => ({})));
    return jsonResponse(getGatewayRuntime().createSession(body.title), { status: 201 });
  } catch (error) {
    return errorResponse(error);
  }
}
