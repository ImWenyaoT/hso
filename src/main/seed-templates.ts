import Database from 'better-sqlite3'

/** v1 预定义模板 fixture 数据 */
const TEMPLATE_FIXTURES = [
  {
    id: 'tpl-generic-article',
    slug: 'generic-article',
    display_name: 'Generic Article',
    template_version: '1.0.0',
    supported_section_keys: JSON.stringify([
      'title', 'abstract', 'introduction', 'related_work',
      'method', 'results', 'conclusion', 'references_placeholder'
    ]),
    mapping_rules: JSON.stringify({
      title: 'title',
      abstract: 'abstract',
      introduction: 'section',
      related_work: 'section',
      method: 'section',
      results: 'section',
      conclusion: 'section',
      references_placeholder: 'bibliography'
    })
  },
  {
    id: 'tpl-ieee',
    slug: 'ieee',
    display_name: 'IEEE Conference',
    template_version: '1.0.0',
    supported_section_keys: JSON.stringify([
      'title', 'abstract', 'introduction', 'related_work',
      'method', 'results', 'conclusion', 'references_placeholder'
    ]),
    mapping_rules: JSON.stringify({
      title: 'IEEEtitle',
      abstract: 'IEEEabstract',
      introduction: 'section',
      related_work: 'section',
      method: 'section',
      results: 'section',
      conclusion: 'section',
      references_placeholder: 'bibliography'
    })
  },
  {
    id: 'tpl-elsevier',
    slug: 'elsevier',
    display_name: 'Elsevier Journal',
    template_version: '1.0.0',
    supported_section_keys: JSON.stringify([
      'title', 'abstract', 'introduction', 'related_work',
      'method', 'results', 'conclusion', 'references_placeholder'
    ]),
    mapping_rules: JSON.stringify({
      title: 'title',
      abstract: 'abstract',
      introduction: 'section',
      related_work: 'section',
      method: 'section',
      results: 'section',
      conclusion: 'section',
      references_placeholder: 'bibliography'
    })
  }
]

/**
 * 插入模板 fixture
 * 幂等操作：仅在 template 表为空时执行
 */
export function seedTemplates(sqlite: Database.Database): void {
  const count = (sqlite.prepare('SELECT COUNT(*) as cnt FROM template').get() as { cnt: number }).cnt
  if (count > 0) return

  const insert = sqlite.prepare(`
    INSERT INTO template (id, slug, display_name, template_version, supported_section_keys, mapping_rules)
    VALUES (@id, @slug, @display_name, @template_version, @supported_section_keys, @mapping_rules)
  `)

  const insertAll = sqlite.transaction((templates: typeof TEMPLATE_FIXTURES) => {
    for (const t of templates) insert.run(t)
  })

  insertAll(TEMPLATE_FIXTURES)
  console.log(`[DB] seeded ${TEMPLATE_FIXTURES.length} templates`)
}