const {
  app,
  BrowserWindow,
  Menu,
  dialog,
  ipcMain,
  session,
  shell,
  systemPreferences,
} = require("electron");
const path = require("node:path");
const fs = require("node:fs");
const { startBackend, projectRoot } = require("./backend.cjs");
const { Permissions } = require("./permissions.cjs");
const {
  trustedPage,
  allowedPermission,
  previewPrefix,
} = require("./security.cjs");
const fake = process.argv.includes("--fake");
let backend,
  window,
  quitting = false;
app.setName("Catbot");
if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on("second-instance", () => {
    if (window) {
      if (window.isMinimized()) window.restore();
      window.show();
      window.focus();
    }
  });
  app
    .whenReady()
    .then(start)
    .catch((error) => {
      dialog.showErrorBox("Billu could not start", error.message);
      app.quit();
    });
}
async function preview(url) {
  const prefix = previewPrefix(url, backend.origin);
  if (!prefix) return;
  const isolated = session.fromPartition(`preview-${Date.now()}`);
  isolated.setPermissionRequestHandler((_wc, _permission, callback) =>
    callback(false),
  );
  isolated.setPermissionCheckHandler(() => false);
  isolated.webRequest.onBeforeRequest((details, callback) =>
    callback({
      cancel:
        !details.url.startsWith(prefix) && !details.url.startsWith("data:"),
    }),
  );
  isolated.webRequest.onBeforeSendHeaders((details, callback) => {
    if (details.url.startsWith(prefix))
      details.requestHeaders.Authorization = `Bearer ${backend.token}`;
    callback({ requestHeaders: details.requestHeaders });
  });
  const child = new BrowserWindow({
    title: "Billu’s app · Catbot",
    width: 850,
    height: 720,
    webPreferences: {
      session: isolated,
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  child.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  child.webContents.on("will-navigate", (event, target) => {
    if (!target.startsWith(prefix)) event.preventDefault();
  });
  await child.loadURL(url);
}
async function start() {
  const root = projectRoot(process.resourcesPath, app.isPackaged);
  backend = await startBackend(root, fake);
  const permissions = new Permissions({
    systemPreferences,
    shell,
    fake: backend.fake,
  });
  const onboardingFile = path.join(
    app.getPath("userData"),
    "permissions-requested.json",
  );
  const trusted = session.fromPartition("persist:catbot-desktop");
  trusted.webRequest.onBeforeSendHeaders((details, callback) => {
    const normalized = details.url.replace(/^ws:/, "http:");
    if (normalized.startsWith(`${backend.origin}/`))
      details.requestHeaders.Authorization = `Bearer ${backend.token}`;
    callback({ requestHeaders: details.requestHeaders });
  });
  trusted.setPermissionCheckHandler(
    (wc, permission, requestingOrigin, details) =>
      wc === window?.webContents &&
      trustedPage(wc.getURL(), backend.origin) &&
      ["media", "microphone", "audioCapture"].includes(permission) &&
      details?.mediaType !== "video" &&
      trustedPage(requestingOrigin, backend.origin),
  );
  trusted.setPermissionRequestHandler(
    async (wc, permission, callback, details) => {
      if (
        wc !== window?.webContents ||
        !trustedPage(wc.getURL(), backend.origin) ||
        !allowedPermission(permission, details) ||
        !trustedPage(details.requestingUrl || wc.getURL(), backend.origin)
      )
        return callback(false);
      if (backend.fake) return callback(false);
      try {
        // Capture may request the initial OS prompt, but only the explicit
        // permission setup action should navigate away to System Settings.
        const status = await permissions.request("microphone", {
          openSettings: false,
        });
        callback(["granted", "request-on-use"].includes(status.microphone));
      } catch {
        callback(false);
      }
    },
  );
  window = new BrowserWindow({
    title: "Catbot · Billu",
    width: 1440,
    height: 940,
    minWidth: 850,
    minHeight: 650,
    backgroundColor: "#0B0A10",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      additionalArguments: process.argv.includes("--smoke")
        ? ["--catbot-smoke"]
        : [],
      session: trusted,
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      autoplayPolicy: "no-user-gesture-required",
    },
  });
  const authenticate = (event) => {
    if (
      event.sender !== window.webContents ||
      !trustedPage(event.senderFrame?.url, backend.origin)
    )
      throw new Error("Only Billu’s main window can request native access.");
  };
  ipcMain.handle("catbot:permissions", (event) => {
    authenticate(event);
    return {
      ...permissions.status(),
      firstRun: !fs.existsSync(onboardingFile),
    };
  });
  ipcMain.handle("catbot:finish-onboarding", (event) => {
    authenticate(event);
    fs.writeFileSync(onboardingFile, JSON.stringify({ requested: true }));
    return true;
  });
  ipcMain.handle("catbot:request-permission", async (event, kind) => {
    authenticate(event);
    return permissions.request(kind);
  });
  ipcMain.handle("catbot:volume-status", async (event) => {
    authenticate(event);
    return permissions.volumeStatus();
  });
  window.webContents.on("will-navigate", (event, target) => {
    if (!trustedPage(target, backend.origin)) event.preventDefault();
  });
  window.webContents.setWindowOpenHandler(({ url }) => {
    void preview(url);
    return { action: "deny" };
  });
  window.once("ready-to-show", () => window.show());
  window.on("closed", () => {
    window = null;
    app.quit();
  });
  backend.child.on("exit", () => {
    if (!quitting && window) {
      dialog.showErrorBox(
        "Billu disconnected",
        "The Python backend stopped. Relaunch Catbot to reconnect.",
      );
      app.quit();
    }
  });
  Menu.setApplicationMenu(
    Menu.buildFromTemplate([
      {
        label: "Catbot",
        submenu: [
          { role: "about" },
          { type: "separator" },
          { role: "hide" },
          { role: "unhide" },
          { type: "separator" },
          { role: "quit" },
        ],
      },
      { role: "editMenu" },
      { role: "viewMenu" },
      { role: "windowMenu" },
    ]),
  );
  await window.loadURL(backend.origin);
  if (process.argv.includes("--smoke")) {
    let passed = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      const response = await fetch(backend.origin + "/api/stats", {
        headers: { Authorization: `Bearer ${backend.token}` },
      });
      const stats = await response.json();
      const last = stats.voice?.last;
      if (last?.status === "completed") {
        console.log(
          "CATBOT_DESKTOP_SMOKE " +
            JSON.stringify({
              electron: process.versions.electron,
              backend: true,
              rendererAudioConnected: stats.voice.connected,
              voice: last,
            }),
        );
        passed = last.provider === (stats.fake ? "system" : "sarvam");
        break;
      }
      if (last?.status === "failed") break;
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
    if (!passed) {
      console.error(
        "Desktop voice smoke did not complete with the expected provider.",
      );
      process.exitCode = 1;
    }
    app.quit();
  }
}
app.on("window-all-closed", () => app.quit());
app.on("before-quit", (event) => {
  if (quitting || !backend) return;
  event.preventDefault();
  quitting = true;
  backend.stop().finally(() => app.quit());
});
