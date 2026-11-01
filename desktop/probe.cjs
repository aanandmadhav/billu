const { app, BrowserWindow, systemPreferences } = require("electron");
app.whenReady().then(async () => {
  const window = new BrowserWindow({
    show: false,
    webPreferences: {
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      autoplayPolicy: "no-user-gesture-required",
    },
  });
  await window.loadURL("data:text/html,<title>Catbot runtime probe</title>");
  console.log(
    JSON.stringify({
      electron: process.versions.electron,
      microphone: systemPreferences.getMediaAccessStatus("microphone"),
      accessibility: systemPreferences.isTrustedAccessibilityClient(false),
      askForMediaAccess: typeof systemPreferences.askForMediaAccess,
      sessionPermissions:
        typeof window.webContents.session.setPermissionRequestHandler,
    }),
  );
  window.webContents.on("console-message", (_event, ...args) => {
    const message = args.find(
      (value) =>
        typeof value === "string" && value.startsWith("CATBOT_VOICE_PROBE "),
    );
    if (message) {
      console.log(message);
      app.quit();
    }
  });
  await window.loadFile(require("node:path").join(__dirname, "probe.html"));
  setTimeout(() => {
    console.log("VOICE_PROBE_TIMEOUT");
    app.exit(1);
  }, 20000);
});
