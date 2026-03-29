import { defineConfig } from 'drizzle-kit'

export default defineConfig({
  schema: './src/shared/schema.ts',
  out: './drizzle',
  dialect: 'sqlite',
  dbCredentials: {
    url: './hso-dev.db'
  }
})
