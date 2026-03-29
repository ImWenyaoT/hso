import { randomUUID } from 'crypto'

/**
 * 生成 UUID v4 作为实体 ID
 * Node.js 内置 crypto 模块，无需外部依赖
 */
export function newId(): string {
  return randomUUID()
}

/**
 * 生成当前 UTC 时间的 ISO 8601 字符串
 */
export function now(): string {
  return new Date().toISOString()
}
