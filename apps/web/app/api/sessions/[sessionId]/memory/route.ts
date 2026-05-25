import {
  errorResponse,
  getGatewayRuntime,
  jsonResponse,
  sessionIdFromContext
} from "../../../../lib/gateway";

export const runtime = "nodejs";

/** Lists persisted memory records for one session. */
export async function GET(
  _request: Request,
  context: { params: Promise<{ sessionId: string }> }
): Promise<Response> {
  try {
    const sessionId = await sessionIdFromContext(context);
    return jsonResponse(getGatewayRuntime().listMemory(sessionId));
  } catch (error) {
    return errorResponse(error);
  }
}
