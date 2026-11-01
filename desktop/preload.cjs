const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld(
  "catbotDesktop",
  Object.freeze({
    platform: process.platform,
    getViewMode: () => ipcRenderer.invoke("catbot:get-view-mode"),
    setViewMode: (mode) => ipcRenderer.invoke("catbot:set-view-mode", mode),
    smoke: process.argv.includes("--catbot-smoke"),
    completeSetup: () => ipcRenderer.invoke("catbot:finish-onboarding"),
    permissions: () => ipcRenderer.invoke("catbot:permissions"),
    requestPermission: (kind) =>
      ipcRenderer.invoke("catbot:request-permission", kind),
    volumeStatus: () => ipcRenderer.invoke("catbot:volume-status"),
  }),
);
