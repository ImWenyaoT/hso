import { ElectronAPI } from '@electron-toolkit/preload'

declare global {
  interface Window {
    electron: ElectronAPI
    api: {
      invoke: (channel: string, ...args: unknown[]) => Promise<unknown>
    }
  }
}
