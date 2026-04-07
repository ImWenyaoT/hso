module.exports = {
  root: true,
  extends: ['@electron-toolkit/eslint-config-ts/recommended'],
  env: {
    node: true
  },
  ignorePatterns: ['out', 'dist', 'node_modules'],
  overrides: [
    {
      files: ['src/renderer/**/*.ts', 'src/renderer/**/*.tsx'],
      env: {
        browser: true
      }
    },
    {
      files: ['tests/**/*.ts'],
      env: {
        node: true
      }
    }
  ]
}