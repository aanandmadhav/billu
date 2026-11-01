const { test } = require("node:test");
const assert = require("node:assert/strict");
const {
  trustedPage,
  allowedPermission,
  previewPrefix,
} = require("../security.cjs");
const { Permissions } = require("../permissions.cjs");

test("only the exact local main page can request native access", () => {
  const origin = "http://127.0.0.1:1234";
  assert.equal(trustedPage(origin + "/", origin), true);
  for (const url of [
    origin + "/apps/test/index.html",
    "https://evil.test/",
    origin + ".evil.test/",
    "file:///tmp/index.html",
  ])
    assert.equal(trustedPage(url, origin), false);
  assert.equal(allowedPermission("media", { mediaTypes: ["audio"] }), true);
  assert.equal(
    allowedPermission("media", { mediaTypes: ["audio", "video"] }),
    false,
  );
  assert.equal(allowedPermission("camera"), false);
  assert.equal(allowedPermission("media", {}), false);
});
test("app previews are restricted to their app and never get the native preload", () => {
  const origin = "http://127.0.0.1:1234",
    id = "a".repeat(32);
  assert.equal(
    previewPrefix(`${origin}/apps/${id}/index.html`, origin),
    `${origin}/apps/${id}/`,
  );
  assert.equal(previewPrefix(`${origin}/api/text`, origin), null);
  assert.equal(
    previewPrefix(`https://evil.test/apps/${id}/index.html`, origin),
    null,
  );
});
test("microphone permission prompts once; denied access opens settings", async () => {
  const calls = [];
  let status = "not-determined";
  const permissions = new Permissions({
    platform: "darwin",
    fake: false,
    systemPreferences: {
      getMediaAccessStatus: () => status,
      askForMediaAccess: async (kind) => {
        calls.push(kind);
        status = "granted";
      },
      isTrustedAccessibilityClient: () => true,
    },
    shell: { openExternal: async (url) => calls.push(url) },
  });
  assert.equal((await permissions.request("microphone")).microphone, "granted");
  await permissions.request("microphone");
  assert.deepEqual(calls, ["microphone"]);
  status = "denied";
  for (let attempt = 0; attempt < 2; attempt++) {
    assert.equal(
      (await permissions.request("microphone", { openSettings: false }))
        .microphone,
      "denied",
    );
  }
  assert.deepEqual(calls, ["microphone"]);
  await permissions.request("microphone");
  assert.match(calls.at(-1), /Privacy_Microphone/);
  await assert.rejects(permissions.request("camera"));
});
test("fake mode never invokes native permission or volume APIs", async () => {
  const fail = () => {
    throw new Error("native access in fake mode");
  };
  const permissions = new Permissions({
    platform: "darwin",
    fake: true,
    systemPreferences: new Proxy({}, { get: () => fail }),
    shell: { openExternal: fail },
  });
  assert.equal((await permissions.request("microphone")).microphone, "demo");
  assert.equal(
    (await permissions.request("accessibility")).accessibility,
    "demo",
  );
  assert.equal((await permissions.volumeStatus()).demo, true);
});

test("screenshot previews accept only fixed local capture IDs", () => {
  const origin = "http://127.0.0.1:1234";
  const url = `${origin}/captures/${"b".repeat(32)}.png`;
  assert.equal(previewPrefix(url, origin), url);
  assert.equal(previewPrefix(`${origin}/captures/../secret.png`, origin), null);
  assert.equal(
    previewPrefix(`https://evil.test/captures/${"b".repeat(32)}.png`, origin),
    null,
  );
});

test("screen permission is reported and Settings opens only on explicit request", async () => {
  const opened = [];
  const types = [];
  const permissions = new Permissions({
    platform: "darwin",
    fake: false,
    systemPreferences: {
      getMediaAccessStatus: (type) => {
        types.push(type);
        return type === "screen" ? "denied" : "granted";
      },
      isTrustedAccessibilityClient: () => true,
    },
    shell: { openExternal: async (url) => opened.push(url) },
  });
  assert.equal(permissions.status().screen, "denied");
  assert(types.includes("screen"));
  assert.equal(opened.length, 0);
  await permissions.request("screen");
  assert.match(opened[0], /Privacy_ScreenCapture/);
});
