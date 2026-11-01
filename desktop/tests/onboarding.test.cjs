const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");

test("denied microphone stays on its settings step before asking for Accessibility", async () => {
  const elements = new Map(),
    listeners = new Map(),
    requests = [];
  let permissions = {
    microphone: "denied",
    accessibility: "not-granted",
    firstRun: true,
  };
  const element = (id) => {
    if (!elements.has(id))
      elements.set(id, { style: {}, addEventListener() {}, focus() {} });
    return elements.get(id);
  };
  global.document = {
    getElementById: element,
    body: { classList: { add() {} } },
  };
  global.window = {
    catbotDesktop: {
      permissions: async () => ({ ...permissions }),
      volumeStatus: async () => ({ level: 50, muted: false, available: true }),
      requestPermission: async (kind) => {
        requests.push(kind);
        return { ...permissions };
      },
      completeSetup: async () => {
        permissions.firstRun = false;
      },
    },
    addEventListener: (name, fn) => listeners.set(name, fn),
  };
  global.fetch = async (url) => ({
    ok: true,
    json: async () => (url === "/api/stats" ? { fake: false } : { ok: true }),
  });
  const source = readFileSync(
    path.resolve(__dirname, "../../catbot/ui/desktop.js"),
    "utf8",
  );
  const { setupDesktop } = await import(
    "data:text/javascript;base64," + Buffer.from(source).toString("base64")
  );
  await setupDesktop(
    { setEnabled: async () => {}, ready: async () => {} },
    () => {},
  );
  assert.deepEqual(requests, ["microphone"]);
  assert.equal(permissions.firstRun, true);
  permissions.microphone = "granted";
  await listeners.get("focus")();
  assert.deepEqual(requests, ["microphone", "accessibility"]);
  assert.equal(permissions.firstRun, false);
});
