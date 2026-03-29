import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

/**
 * 暴露给渲染进程的 API
 * - electronAPI: electron-toolkit 默认工具（ipcRenderer 封装等）
 * - api: HSO 业务 IPC 封装
 */
contextBridge.exposeInMainWorld('electron', electronAPI)

contextBridge.exposeInMainWorld('api', {
  /**
   * 通用 invoke 封装，渲染层通过 window.api.invoke(channel, ...args) 调用
   */
  invoke: (channel: string, ...args: unknown[]) => ipcRenderer.invoke(channel, ...args)
})
