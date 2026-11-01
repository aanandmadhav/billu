const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

test("rapid release/repress discards the old microphone request without stopping the new one", async () => {
  const controls = [],
    requests = [];
  global.window = global;
  global.location = { protocol: "http:", host: "127.0.0.1:1234" };
  global.speechSynthesis = { cancel() {} };
  class Socket {
    static OPEN = 1;
    constructor() {
      this.readyState = 1;
    }
    send(value) {
      controls.push(JSON.parse(value));
    }
  }
  global.WebSocket = Socket;
  global.AudioContext = class {
    constructor() {
      this.state = "running";
      this.destination = {};
      this.audioWorklet = { addModule: async () => {} };
    }
    async resume() {}
    createMediaStreamSource() {
      return { connect() {}, disconnect() {} };
    }
  };
  global.AudioWorkletNode = class {
    constructor() {
      this.port = {
        onmessage: null,
        close() {},
        postMessage: () =>
          queueMicrotask(() =>
            this.port.onmessage?.({ data: { final: true } }),
          ),
      };
    }
    connect() {}
    disconnect() {}
  };
  Object.defineProperty(global, "navigator", {
    configurable: true,
    value: {
      mediaDevices: {
        getUserMedia: () => new Promise((resolve) => requests.push(resolve)),
      },
    },
  });
  const source = fs.readFileSync(
    path.resolve(__dirname, "../../catbot/ui/audio.js"),
    "utf8",
  );
  const { AudioController } = await import(
    "data:text/javascript;base64," + Buffer.from(source).toString("base64")
  );
  const audio = new AudioController(() => {});
  audio.fake = false;
  const tick = () => new Promise((resolve) => setImmediate(resolve));
  const first = audio.start();
  await tick();
  assert.equal(requests.length, 1);
  await audio.stop();
  const second = audio.start();
  await tick();
  assert.equal(requests.length, 2);
  let oldStops = 0,
    newStops = 0;
  requests[0]({
    getTracks: () => [
      {
        stop() {
          oldStops++;
        },
      },
    ],
  });
  assert.equal(await first, false);
  assert.equal(oldStops, 1);
  assert.equal(
    audio.recording,
    true,
    "An old permission result must not cancel the new capture",
  );
  const track = {
    stop() {
      newStops++;
    },
  };
  requests[1]({ getTracks: () => [track] });
  assert.equal(await second, true);
  assert.equal(
    controls.filter((message) => message.type === "start").length,
    1,
  );
  await audio.socket.onmessage({
    data: JSON.stringify({
      type: "error",
      message: "Try again",
      stop_recording: true,
    }),
  });
  assert.equal(audio.recording, false);
  assert.equal(newStops, 1);
  assert.equal(audio.worklet, null);
});

test("release while audio is unlocking does not open the microphone later", async () => {
  const requests = [];
  let unlock;
  global.window = global;
  global.location = { protocol: "http:", host: "127.0.0.1:1234" };
  global.WebSocket = class {
    static OPEN = 1;
    constructor() {
      this.readyState = 1;
    }
    send() {}
  };
  global.speechSynthesis = { cancel() {} };
  global.AudioContext = class {
    constructor() {
      this.state = "suspended";
    }
    resume() {
      return new Promise((resolve) => {
        unlock = () => {
          this.state = "running";
          resolve();
        };
      });
    }
  };
  Object.defineProperty(global, "navigator", {
    configurable: true,
    value: { mediaDevices: { getUserMedia: () => requests.push(true) } },
  });
  const source = fs.readFileSync(
    path.resolve(__dirname, "../../catbot/ui/audio.js"),
    "utf8",
  );
  const { AudioController } = await import(
    "data:text/javascript;base64," + Buffer.from(source).toString("base64")
  );
  const audio = new AudioController(() => {});
  audio.fake = false;
  const pending = audio.start();
  await audio.stop();
  unlock();
  assert.equal(await pending, false);
  assert.equal(requests.length, 0);
});

test("a blocked microphone reports how to enable it from simple mode", async () => {
  global.window = global;
  global.catbotDesktop = {};
  global.location = { protocol: "http:", host: "127.0.0.1:1234" };
  global.speechSynthesis = { cancel() {} };
  global.WebSocket = class {
    static OPEN = 1;
    constructor() {
      this.readyState = 1;
    }
    send() {}
  };
  global.AudioContext = class {
    constructor() {
      this.state = "running";
    }
    async resume() {}
  };
  Object.defineProperty(global, "navigator", {
    configurable: true,
    value: {
      mediaDevices: {
        getUserMedia: async () => {
          throw Object.assign(new Error("Denied"), { name: "NotAllowedError" });
        },
      },
    },
  });
  const source = fs.readFileSync(
    path.resolve(__dirname, "../../catbot/ui/audio.js"),
    "utf8",
  );
  const { AudioController } = await import(
    "data:text/javascript;base64," + Buffer.from(source).toString("base64")
  );
  const notices = [];
  const audio = new AudioController((message) => notices.push(message));
  audio.fake = false;
  assert.equal(await audio.start(), false);
  assert.equal(audio.recording, false);
  assert.match(
    notices.at(-1),
    /Full dashboard.*Permissions.*Enable microphone/,
  );
  delete global.catbotDesktop;
});
