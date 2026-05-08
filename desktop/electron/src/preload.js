/* preload.js — runs in an isolated world, exposes a tiny readonly bridge.
 *
 * Per repo policy: nodeIntegration:false, contextIsolation:true, sandbox:true.
 * The chatbot must work identically in browser and Electron.
 *
 * Surface (frozen):
 *   window.desktopAPI.isDesktop          → true
 *   window.desktopAPI.platform           → 'win32' | 'darwin' | 'linux'
 *   window.desktopAPI.window.minimize()
 *   window.desktopAPI.window.maximize()  → returns Promise<bool isMaxed>
 *   window.desktopAPI.window.close()
 *   window.desktopAPI.window.isMaximized() → Promise<bool>
 *   window.desktopAPI.window.onMaximizedChanged(cb)  → unsubscribe()
 *   window.desktopAPI.tray.setBadge(n)    → Promise<n>
 *   window.desktopAPI.notify.show({ title, body, silent })  → Promise<bool>
 *
 * No fs, no shell, no arbitrary ipc.
 */
const { contextBridge, ipcRenderer } = require('electron');

const api = Object.freeze({
    isDesktop: true,
    platform: process.platform,
    window: Object.freeze({
        minimize:    () => ipcRenderer.invoke('window:minimize'),
        maximize:    () => ipcRenderer.invoke('window:maximize'),
        close:       () => ipcRenderer.invoke('window:close'),
        isMaximized: () => ipcRenderer.invoke('window:isMaximized'),
        onMaximizedChanged(cb) {
            const handler = (_e, isMax) => { try { cb(!!isMax); } catch (_) {} };
            ipcRenderer.on('window:maximized-changed', handler);
            return () => ipcRenderer.removeListener('window:maximized-changed', handler);
        }
    }),
    tray: Object.freeze({
        setBadge: (count) => ipcRenderer.invoke('tray:setBadge', count)
    }),
    notify: Object.freeze({
        show: (payload) => ipcRenderer.invoke('notify:show', payload || {})
    })
});

contextBridge.exposeInMainWorld('desktopAPI', api);
