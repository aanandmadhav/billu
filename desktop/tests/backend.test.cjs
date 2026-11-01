const { test } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { startBackend } = require("../backend.cjs");

test("Electron owns an authenticated backend, uses a free port, and cleans it up", async () => {
  const backend = await startBackend(path.resolve(__dirname, "../.."), true);
  try {
    assert.equal((await fetch(backend.origin + "/api/stats")).status, 401);
    const headers = { Authorization: `Bearer ${backend.token}` };
    const response = await fetch(backend.origin + "/api/stats", { headers });
    assert.equal(response.status, 200);
    assert.equal((await response.json()).fake, true);
    const blocked = await fetch(backend.origin + "/api/text", {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ utterance: "saari files delete kar do" }),
    });
    assert.equal(blocked.status, 202);
  } finally {
    await backend.stop();
  }
  await assert.rejects(fetch(backend.origin + "/api/stats"));
});
