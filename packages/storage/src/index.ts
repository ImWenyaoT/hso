import { existsSync, mkdirSync, readFileSync } from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";
import {
  GatewayEvent,
  MemoryRecord,
  SessionRecord,
  gatewayEventSchema,
  makeMemoryRecord,
  makeSessionRecord,
  memoryRecordSchema,
  sessionRecordSchema,
  type JsonObject
} from "@hso/shared";

export type GatewayStoreOptions = {
  dataDir?: string;
  legacyJsonlPath?: string | null;
};

export class GatewayStore {
  private readonly gatewayDb: Database.Database;
  private readonly memoryDb: Database.Database;

  /** Opens the gateway and memory SQLite databases under the configured data dir. */
  constructor(options: GatewayStoreOptions = {}) {
    const dataDir = options.dataDir ?? defaultGatewayDataDir();
    mkdirSync(dataDir, { recursive: true });
    this.gatewayDb = new Database(path.join(dataDir, "gateway.sqlite3"), sqliteOptions());
    this.memoryDb = new Database(path.join(dataDir, "memory.sqlite3"), sqliteOptions());
    this.gatewayDb.pragma("foreign_keys = ON");
    this.ensureGatewaySchema();
    this.ensureMemorySchema();
    if (options.legacyJsonlPath !== null) {
      this.migrateLegacyMemory(options.legacyJsonlPath ?? path.join(dataDir, "memory.jsonl"));
    }
  }

  /** Creates and persists a new local gateway session. */
  createSession(title = "Untitled session"): SessionRecord {
    const session = makeSessionRecord(title);
    this.saveSession(session);
    return session;
  }

  /** Upserts a session record after schema validation. */
  saveSession(session: SessionRecord): void {
    const payload = sessionRecordSchema.parse(session);
    this.gatewayDb
      .prepare(
        `
        INSERT INTO gateway_sessions (id, title, created_at)
        VALUES (@id, @title, @created_at)
        ON CONFLICT(id) DO UPDATE SET
          title = excluded.title,
          created_at = excluded.created_at
        `
      )
      .run(payload);
  }

  /** Lists sessions in creation order. */
  listSessions(): SessionRecord[] {
    const rows = this.gatewayDb
      .prepare("SELECT id, title, created_at FROM gateway_sessions ORDER BY created_at ASC, id ASC")
      .all();
    return rows.map((row) => sessionRecordSchema.parse(row));
  }

  /** Returns one session or throws UnknownSessionError for stable route mapping. */
  getSession(sessionId: string): SessionRecord {
    const row = this.gatewayDb
      .prepare("SELECT id, title, created_at FROM gateway_sessions WHERE id = ?")
      .get(sessionId);
    if (!row) {
      throw new UnknownSessionError(sessionId);
    }
    return sessionRecordSchema.parse(row);
  }

  /** Persists a batch of gateway events transactionally. */
  saveEvents(events: GatewayEvent[]): void {
    if (events.length === 0) {
      return;
    }
    const insert = this.gatewayDb.prepare(
      `
      INSERT INTO gateway_events (
        id, session_id, type, message, agent_name, payload_json, created_at
      )
      VALUES (@id, @session_id, @type, @message, @agent_name, @payload_json, @created_at)
      ON CONFLICT(id) DO UPDATE SET
        type = excluded.type,
        message = excluded.message,
        agent_name = excluded.agent_name,
        payload_json = excluded.payload_json,
        created_at = excluded.created_at
      `
    );
    const transaction = this.gatewayDb.transaction((batch: GatewayEvent[]) => {
      for (const event of batch) {
        const payload = gatewayEventSchema.parse(event);
        insert.run({
          ...payload,
          payload_json: JSON.stringify(payload.payload)
        });
      }
    });
    transaction(events);
  }

  /** Lists events for a session in insertion order. */
  listEvents(sessionId: string): GatewayEvent[] {
    this.getSession(sessionId);
    const rows = this.gatewayDb
      .prepare(
        `
        SELECT id, session_id, type, message, agent_name, payload_json, created_at
        FROM gateway_events
        WHERE session_id = ?
        ORDER BY rowid ASC
        `
      )
      .all(sessionId);
    return rows.map((row) => {
      const item = row as Record<string, unknown> & { payload_json: string };
      return gatewayEventSchema.parse({
        ...item,
        payload: JSON.parse(item.payload_json)
      });
    });
  }

  /** Appends one memory record to the memory database. */
  appendMemory(input: {
    session_id: string;
    role: string;
    content: string;
    metadata?: JsonObject;
  }): MemoryRecord {
    const record = makeMemoryRecord(input);
    const payload = memoryRecordSchema.parse(record);
    this.memoryDb
      .prepare(
        `
        INSERT INTO memory_records (
          id, session_id, role, content, metadata_json, created_at
        )
        VALUES (@id, @session_id, @role, @content, @metadata_json, @created_at)
        `
      )
      .run({
        ...payload,
        metadata_json: JSON.stringify(payload.metadata)
      });
    return record;
  }

  /** Lists memory records globally or for one session in insertion order. */
  listMemory(sessionId?: string): MemoryRecord[] {
    const rows =
      sessionId === undefined
        ? this.memoryDb
            .prepare(
              `
              SELECT id, session_id, role, content, metadata_json, created_at
              FROM memory_records
              ORDER BY rowid ASC
              `
            )
            .all()
        : this.memoryDb
            .prepare(
              `
              SELECT id, session_id, role, content, metadata_json, created_at
              FROM memory_records
              WHERE session_id = ?
              ORDER BY rowid ASC
              `
            )
            .all(sessionId);
    return rows.map((row) => {
      const item = row as Record<string, unknown> & { metadata_json: string };
      return memoryRecordSchema.parse({
        ...item,
        metadata: JSON.parse(item.metadata_json)
      });
    });
  }

  /** Closes both SQLite database handles. */
  close(): void {
    this.gatewayDb.close();
    this.memoryDb.close();
  }

  /** Creates the gateway session and event tables if they are missing. */
  private ensureGatewaySchema(): void {
    this.gatewayDb.exec(`
      CREATE TABLE IF NOT EXISTS gateway_sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS gateway_events (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        type TEXT NOT NULL,
        message TEXT NOT NULL,
        agent_name TEXT,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (session_id)
          REFERENCES gateway_sessions(id)
          ON DELETE CASCADE
      );

      CREATE INDEX IF NOT EXISTS idx_gateway_events_session_created
        ON gateway_events(session_id, created_at, id);
    `);
  }

  /** Creates the memory table if it is missing. */
  private ensureMemorySchema(): void {
    this.memoryDb.exec(`
      CREATE TABLE IF NOT EXISTS memory_records (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        created_at TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_memory_records_session_created
        ON memory_records(session_id, created_at, id);
    `);
  }

  /** Imports legacy JSONL memory once when a legacy file exists. */
  private migrateLegacyMemory(legacyJsonlPath: string): void {
    if (!existsSync(legacyJsonlPath) || this.listMemory().length > 0) {
      return;
    }
    const records = readFileSync(legacyJsonlPath, "utf8")
      .split(/\r?\n/)
      .filter((line) => line.trim().length > 0)
      .map((line) => memoryRecordSchema.parse(JSON.parse(line)));
    if (records.length === 0) {
      return;
    }
    const insert = this.memoryDb.prepare(
      `
      INSERT OR IGNORE INTO memory_records (
        id, session_id, role, content, metadata_json, created_at
      )
      VALUES (@id, @session_id, @role, @content, @metadata_json, @created_at)
      `
    );
    const transaction = this.memoryDb.transaction((batch: MemoryRecord[]) => {
      for (const record of batch) {
        insert.run({
          ...record,
          metadata_json: JSON.stringify(record.metadata)
        });
      }
    });
    transaction(records);
  }
}

export class UnknownSessionError extends Error {
  /** Creates a typed not-found error for gateway route handlers. */
  constructor(sessionId: string) {
    super(`Unknown session: ${sessionId}`);
    this.name = "UnknownSessionError";
  }
}

/** Resolves the default local gateway data directory. */
export function defaultGatewayDataDir(start = process.cwd()): string {
  if (process.env.HSO_DATA_DIR) {
    return path.resolve(process.env.HSO_DATA_DIR);
  }
  return path.join(findWorkspaceRoot(start), "data", "gateway");
}

/** Walks upward to find the npm workspace root. */
function findWorkspaceRoot(start = process.cwd()): string {
  let current = path.resolve(start);
  for (;;) {
    if (existsSync(path.join(current, "package.json")) && existsSync(path.join(current, "apps"))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      return path.resolve(start);
    }
    current = parent;
  }
}

/** Resolves the native better-sqlite3 binding explicitly for bundled route handlers. */
function sqliteOptions(): Database.Options {
  return {
    nativeBinding: resolveSqliteNativeBinding()
  };
}

/** Finds the better-sqlite3 native addon without asking Next to bundle the .node file. */
function resolveSqliteNativeBinding(): string {
  const request = ["better-sqlite3", "build", "Release", "better_sqlite3.node"].join("/");
  const workspaceBinding = path.join(
    findWorkspaceRoot(),
    "packages",
    "storage",
    "node_modules",
    ...request.split("/")
  );
  if (!existsSync(workspaceBinding)) {
    throw new Error(`Missing better-sqlite3 native binding: ${workspaceBinding}`);
  }
  return workspaceBinding;
}
