// desktop/electron/src/preload.js
//
// Minimal preload bridge. Exposes ONLY the two read-only fields allowed
// by the Electron desktop spec:
//
//   window.desktopAPI = {
//     isDesktop: true,
//     platform: <process.platform>,
//   }
//
// Do NOT expose fs, child_process, shell, ipcRenderer, require, or any
// arbitrary command/file APIs. Renderer is sandboxed and contextIsolated.

'use strict';

const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('desktopAPI', Object.freeze({
  isDesktop: true,
  platform: process.platform,
}));
