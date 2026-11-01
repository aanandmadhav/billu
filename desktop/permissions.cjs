const { execFile } = require("node:child_process");
const { promisify } = require("node:util");
const run = promisify(execFile);
const PANES = {
  screen:
    "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
  microphone:
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
  accessibility:
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
};
class Permissions {
  constructor({ systemPreferences, shell, fake, platform = process.platform }) {
    Object.assign(this, { systemPreferences, shell, fake, platform });
  }
  status() {
    if (this.fake)
      return {
        microphone: "demo",
        screen: "demo",
        accessibility: "demo",
        platform: this.platform,
      };
    const microphone = ["darwin", "win32"].includes(this.platform)
      ? this.systemPreferences.getMediaAccessStatus("microphone")
      : "request-on-use";
    const accessibility =
      this.platform === "darwin"
        ? this.systemPreferences.isTrustedAccessibilityClient(false)
          ? "granted"
          : "not-granted"
        : "not-required";
    const screen =
      this.platform === "darwin"
        ? this.systemPreferences.getMediaAccessStatus("screen")
        : "not-required";
    return { microphone, screen, accessibility, platform: this.platform };
  }
  async request(kind, { openSettings = true } = {}) {
    if (!["microphone", "accessibility", "screen"].includes(kind))
      throw new Error("Unknown permission.");
    if (this.fake) return this.status();
    if (this.platform === "darwin") {
      if (kind === "screen") {
        if (
          this.systemPreferences.getMediaAccessStatus("screen") !== "granted" &&
          openSettings
        )
          await this.shell.openExternal(PANES.screen);
      } else if (kind === "microphone") {
        const status =
          this.systemPreferences.getMediaAccessStatus("microphone");
        if (status === "not-determined")
          await this.systemPreferences.askForMediaAccess("microphone");
        else if (status !== "granted" && openSettings)
          await this.shell.openExternal(PANES.microphone);
      } else {
        const trusted =
          this.systemPreferences.isTrustedAccessibilityClient(true);
        if (!trusted) await this.shell.openExternal(PANES.accessibility);
      }
    } else if (
      this.platform === "win32" &&
      kind === "microphone" &&
      openSettings
    ) {
      await this.shell.openExternal("ms-settings:privacy-microphone");
    }
    return this.status();
  }
  async volumeStatus() {
    if (this.fake) return { level: 50, muted: false, demo: true };
    if (this.platform !== "darwin") return { available: false };
    // Read-only setup diagnostic. It never changes volume or executes model-supplied text.
    const { stdout } = await run(
      "/usr/bin/osascript",
      ["-e", "get {output volume, output muted} of (get volume settings)"],
      { timeout: 5000, maxBuffer: 1024 },
    );
    const match = stdout.trim().match(/^(\d+),\s*(true|false)$/);
    return match
      ? { level: Number(match[1]), muted: match[2] === "true", available: true }
      : { available: false };
  }
}
module.exports = { Permissions, PANES };
