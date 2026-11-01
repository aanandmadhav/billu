const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const tick = () => new Promise((resolve) => setImmediate(resolve));

async function harness(start = async () => true) {
  const handlers = { document: {}, window: {}, button: {} };
  const button = {
    dataset: {},
    classList: { add() {}, remove() {} },
    contains: (target) => target === button,
    closest: () => null,
    setPointerCapture() {},
    addEventListener: (type, fn) => {
      handlers.button[type] = fn;
    },
  };
  global.document = {
    addEventListener: (type, fn, capture) => {
      assert.equal(
        capture,
        true,
        "Space must be intercepted before button activation",
      );
      handlers.document[type] = fn;
    },
  };
  global.window = {
    addEventListener: (type, fn) => {
      handlers.window[type] = fn;
    },
  };
  let starts = 0,
    stops = 0,
    listens = 0;
  const notices = [];
  const audio = {
    fake: false,
    async start() {
      starts++;
      return start();
    },
    async stop() {
      stops++;
    },
  };
  const source = fs.readFileSync(
    path.resolve(__dirname, "../../catbot/ui/push-to-talk.js"),
    "utf8",
  );
  const { setupPushToTalk } = await import(
    "data:text/javascript;base64," + Buffer.from(source).toString("base64")
  );
  setupPushToTalk({
    audio,
    button,
    label: {},
    input: { focus() {} },
    notice: (message) => notices.push(message),
    listening: () => listens++,
  });
  function key(type, target = button, extra = {}) {
    const event = {
      target,
      code: "Space",
      key: " ",
      repeat: false,
      preventDefault() {
        this.defaultPrevented = true;
      },
      stopPropagation() {
        this.stopped = true;
      },
      ...extra,
    };
    handlers.document[type](event);
    return event;
  }
  return {
    handlers,
    key,
    button,
    notices,
    counts: () => ({ starts, stops, listens }),
  };
}

test("Space records instead of clicking the focused mode button, including repeats and release", async () => {
  const h = await harness();
  const modeButton = { id: "view-mode", closest: () => null };
  const down = h.key("keydown", modeButton);
  assert.equal(down.defaultPrevented, true);
  assert.equal(down.stopped, true);
  assert.match(h.notices[0], /Opening microphone/);
  assert.equal(
    h.key("keydown", modeButton, { repeat: true }).defaultPrevented,
    true,
  );
  await tick();
  assert.equal(h.counts().starts, 1);
  assert.equal(h.counts().listens, 1);
  assert.equal(h.key("keyup", modeButton).defaultPrevented, true);
  await tick();
  assert.equal(h.counts().stops, 1);
});

test("typing, dialogs and modified Space retain their normal keyboard behavior", async () => {
  const h = await harness();
  for (const target of [{ closest: () => ({}) }, { closest: () => null }]) {
    const event = h.key(
      "keydown",
      target,
      target.closest() ? {} : { metaKey: true },
    );
    assert.equal(event.defaultPrevented, undefined);
  }
  assert.equal(h.counts().starts, 0);
});

test("mic pointer capture failures do not prevent recording and cancellation stops it", async () => {
  const h = await harness();
  h.button.setPointerCapture = () => {
    throw new Error("Pointer is no longer active");
  };
  h.handlers.button.pointerdown({
    button: 0,
    pointerId: 1,
    preventDefault() {},
  });
  await tick();
  assert.equal(h.counts().listens, 1);
  h.handlers.button.pointercancel();
  await tick();
  assert.equal(h.counts().stops, 1);
});

test("release during microphone startup cannot leave the button listening later", async () => {
  let resolve;
  const h = await harness(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  h.key("keydown");
  h.key("keyup");
  resolve(true);
  await tick();
  assert.equal(h.counts().stops, 1);
  assert.equal(h.counts().listens, 0);
  assert.equal(h.button.dataset.pending, undefined);
});
