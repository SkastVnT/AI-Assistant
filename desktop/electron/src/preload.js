/* preload.js — runs in an isolated world, exposes a tiny readonly bridge.
 *
 * Per repo policy: nodeIntegration:false, contextIsolation:true, sandbox:true.
 * The chatbot must work identically in browser and Electron. The only thing
 * the desktop bridge does is announce itself so a future feature can light up
 * desktop-only UI (e.g. an "open output folder" button). It deliberately
 * exposes NO filesystem, NO shell, NO ipc method.
 */
const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('desktopAPI', Object.freeze({
    isDesktop: true,
    platform: process.platform
}));
