import { randomUUID } from "node:crypto";
import { z } from "zod";

const jsonValueSchema: z.ZodType<JsonValue> = z.lazy(() =>
  z.union([
    z.string(),
    z.number(),
    z.boolean(),
    z.null(),
    z.array(jsonValueSchema),
    z.record(z.string(), jsonValueSchema)
  ])
);

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type JsonObject = Record<string, JsonValue>;

export const sessionRecordSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  created_at: z.string().datetime()
});

export const gatewayEventSchema = z.object({
  id: z.string().min(1),
  session_id: z.string().min(1),
  type: z.string().min(1),
  message: z.string(),
  agent_name: z.string().nullable(),
  payload: z.record(z.string(), jsonValueSchema),
  created_at: z.string().datetime()
});

export const memoryRecordSchema = z.object({
  id: z.string().min(1),
  session_id: z.string().min(1),
  role: z.string().min(1),
  content: z.string(),
  metadata: z.record(z.string(), jsonValueSchema),
  created_at: z.string().datetime()
});

export const createSessionRequestSchema = z.object({
  title: z.string().trim().min(1).default("Untitled session")
});

export const sendMessageRequestSchema = z.object({
  content: z.string().trim().min(1)
});

export const sendMessageResponseSchema = z.object({
  session: sessionRecordSchema,
  events: z.array(gatewayEventSchema)
});

export type SessionRecord = z.infer<typeof sessionRecordSchema>;
export type GatewayEvent = z.infer<typeof gatewayEventSchema>;
export type MemoryRecord = z.infer<typeof memoryRecordSchema>;
export type CreateSessionRequest = z.infer<typeof createSessionRequestSchema>;
export type SendMessageRequest = z.infer<typeof sendMessageRequestSchema>;
export type SendMessageResponse = z.infer<typeof sendMessageResponseSchema>;

/** Returns an ISO timestamp for gateway records. */
export function nowIso(): string {
  return new Date().toISOString();
}

/** Creates a compact prefixed id compatible with the legacy JSON shape. */
export function createId(prefix: "ses" | "evt" | "mem"): string {
  return `${prefix}_${randomUUID().replaceAll("-", "")}`;
}

/** Builds and validates a session record before persistence. */
export function makeSessionRecord(title = "Untitled session"): SessionRecord {
  return sessionRecordSchema.parse({
    id: createId("ses"),
    title: title.trim() || "Untitled session",
    created_at: nowIso()
  });
}

/** Builds and validates a gateway event record before persistence. */
export function makeGatewayEvent(input: {
  session_id: string;
  type: string;
  message: string;
  agent_name?: string | null;
  payload?: JsonObject;
}): GatewayEvent {
  return gatewayEventSchema.parse({
    id: createId("evt"),
    session_id: input.session_id,
    type: input.type,
    message: input.message,
    agent_name: input.agent_name ?? null,
    payload: input.payload ?? {},
    created_at: nowIso()
  });
}

/** Builds and validates a memory record before persistence. */
export function makeMemoryRecord(input: {
  session_id: string;
  role: string;
  content: string;
  metadata?: JsonObject;
}): MemoryRecord {
  return memoryRecordSchema.parse({
    id: createId("mem"),
    session_id: input.session_id,
    role: input.role,
    content: input.content,
    metadata: input.metadata ?? {},
    created_at: nowIso()
  });
}
