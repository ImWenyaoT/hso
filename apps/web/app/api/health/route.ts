export const runtime = "nodejs";

/** Reports local TypeScript gateway readiness. */
export async function GET(): Promise<Response> {
  return Response.json({ status: "ok", service: "hso-gateway-ts" });
}
