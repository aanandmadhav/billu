const { test } = require("node:test");
const assert = require("node:assert/strict");
const { startCaptureBridge } = require("../capture.cjs");

test("native capture bridge authenticates the backend, fixes main-display options and never captures in fake mode", async () => {
  let fake = false,
    captures = 0;
  const png = Buffer.from("\x89PNG\r\n\x1a\n", "binary");
  const bridge = await startCaptureBridge({
    isFake: () => fake,
    screen: {
      getPrimaryDisplay: () => ({
        id: 42,
        size: { width: 1200, height: 800 },
        scaleFactor: 2,
      }),
    },
    desktopCapturer: {
      getSources: async (options) => {
        captures++;
        assert.deepEqual(options, {
          types: ["screen"],
          thumbnailSize: { width: 2400, height: 1600 },
          fetchWindowIcons: false,
        });
        return [
          {
            display_id: "42",
            thumbnail: { isEmpty: () => false, toPNG: () => png },
          },
        ];
      },
    },
  });
  const headers = { Authorization: `Bearer ${bridge.token}` };
  try {
    assert.equal(
      (await fetch(bridge.endpoint, { method: "POST" })).status,
      401,
    );
    assert.equal((await fetch(bridge.endpoint, { headers })).status, 400);
    assert.equal(
      (await fetch(bridge.endpoint, { method: "POST", headers, body: "{}" }))
        .status,
      400,
    );
    assert.equal(captures, 0);
    const response = await fetch(bridge.endpoint, { method: "POST", headers });
    assert.equal(response.status, 200);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), png);
    fake = true;
    assert.equal(
      (await fetch(bridge.endpoint, { method: "POST", headers })).status,
      403,
    );
    assert.equal(captures, 1);
  } finally {
    await bridge.close();
  }
});
