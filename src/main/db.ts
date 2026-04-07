import { app } from 'electron'
import { join } from 'path'
import Database from 'better-sqlite3'
import { drizzle } from 'drizzle-orm/better-sqlite3'
import * as schema from '../shared/schema'
import { seedTemplates } from './seed-templates'

let _db: ReturnType<typeof drizzle> | null = null

/**
 * 获取已初始化的 Drizzle DB 实例（单例）
 * 只在主进程中调用
 */
export function getDb(): ReturnType<typeof drizzle> {
  if (!_db) throw new Error('DB not initialized. Call initDb() first.')
  return _db
}

/**
 * 初始化数据库：
 * 1. 确定 DB 文件路径（userData/hso.db）
 * 2. 建表（WAL 模式 + PRAGMA 优化）
 * 3. 插入初始模板 fixture（若为空）
 */
export function initDb(): void {
  const dbPath = join(app.getPath('userData'), 'hso.db')
  const sqlite = new Database(dbPath)

  // 性能优化
  sqlite.pragma('journal_mode = WAL')
  sqlite.pragma('synchronous = NORMAL')
  sqlite.pragma('foreign_keys = ON')

  _db = drizzle(sqlite, { schema })

  // 手动建表（不依赖 migration 文件，适合桌面应用快速启动）
  createTables(sqlite)

  // 插入模板 fixture
  seedTemplates(sqlite)

  console.log(`[DB] initialized at ${dbPath}`)
}

/**
 * 用 raw SQL 创建所有表（IF NOT EXISTS）
 * 保持幂等，可重复执行
 */
function createTables(sqlite: Database.Database): void {
  sqlite.exec(`
    CREATE TABLE IF NOT EXISTS research_card (
      id TEXT PRIMARY KEY,
      input_type TEXT NOT NULL,
      input_value TEXT NOT NULL,
      topic_label TEXT NOT NULL,
      key_papers TEXT NOT NULL DEFAULT '[]',
      trend_summary TEXT NOT NULL DEFAULT '',
      distribution_summary TEXT NOT NULL DEFAULT '',
      project_importable_sections TEXT NOT NULL DEFAULT '[]',
      reference_candidates TEXT NOT NULL DEFAULT '[]',
      notes TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS template (
      id TEXT PRIMARY KEY,
      slug TEXT NOT NULL UNIQUE,
      display_name TEXT NOT NULL,
      template_version TEXT NOT NULL,
      supported_section_keys TEXT NOT NULL DEFAULT '[]',
      mapping_rules TEXT NOT NULL DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS paper_project (
      id TEXT PRIMARY KEY,
      source_research_card_id TEXT REFERENCES research_card(id),
      title TEXT NOT NULL,
      template_id TEXT REFERENCES template(id),
      current_version INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS paper_section (
      id TEXT PRIMARY KEY,
      paper_project_id TEXT NOT NULL REFERENCES paper_project(id) ON DELETE CASCADE,
      order_index INTEGER NOT NULL,
      section_key TEXT NOT NULL,
      heading TEXT NOT NULL,
      content TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS asset (
      id TEXT PRIMARY KEY,
      owner_project_id TEXT NOT NULL REFERENCES paper_project(id),
      name TEXT NOT NULL,
      asset_kind TEXT NOT NULL DEFAULT 'image',
      storage_path TEXT NOT NULL,
      visibility_mode TEXT NOT NULL DEFAULT 'project_only',
      selected_project_ids TEXT NOT NULL DEFAULT '[]',
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS reference_source (
      id TEXT PRIMARY KEY,
      paper_project_id TEXT NOT NULL REFERENCES paper_project(id) ON DELETE CASCADE,
      source_type TEXT NOT NULL,
      source_value TEXT NOT NULL,
      title TEXT NOT NULL,
      authors TEXT NOT NULL DEFAULT '[]',
      publication_year INTEGER,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS build_job (
      id TEXT PRIMARY KEY,
      paper_project_id TEXT NOT NULL REFERENCES paper_project(id),
      project_version INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'queued',
      requested_at TEXT NOT NULL,
      started_at TEXT,
      finished_at TEXT,
      status_summary TEXT
    );

    CREATE TABLE IF NOT EXISTS build_artifact (
      id TEXT PRIMARY KEY,
      build_job_id TEXT NOT NULL REFERENCES build_job(id) ON DELETE CASCADE,
      artifact_kind TEXT NOT NULL,
      storage_path TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS error_event (
      id TEXT PRIMARY KEY,
      paper_project_id TEXT REFERENCES paper_project(id),
      build_job_id TEXT REFERENCES build_job(id),
      stage TEXT NOT NULL,
      error_code TEXT NOT NULL,
      human_summary TEXT NOT NULL,
      location_hint TEXT,
      suggested_fix TEXT,
      created_at TEXT NOT NULL
    );
  `)
}