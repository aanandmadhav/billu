const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");

test("voice unlocks, plays WAV, acknowledges completion, and speaks in fake mode", async () => {
  const messages = [],
    events = [];
  global.location = { protocol: "http:", host: "127.0.0.1:1234" };
  class Socket {
    static OPEN = 1;
    constructor() {
      this.readyState = 1;
    }
    send(message) {
      messages.push(JSON.parse(message));
    }
  }
  global.WebSocket = Socket;
  global.window = global;
  global.speechSynthesis = {
    getVoices: () => [{ localService: true, lang: "en-IN" }],
    cancel() {},
    speak(utterance) {
      events.push("system-speech");
      queueMicrotask(() => utterance.onend());
    },
  };
  global.SpeechSynthesisUtterance = class {
    constructor(text) {
      this.text = text;
    }
  };
  global.AudioContext = class {
    constructor() {
      this.state = "suspended";
      this.destination = {};
    }
    async resume() {
      this.state = "running";
    }
    async decodeAudioData() {
      events.push("wav-decoded");
      return {};
    }
    createBufferSource() {
      return {
        connect() {},
        start() {
          events.push("wav-started");
          queueMicrotask(() => this.onended());
        },
        stop() {},
      };
    }
  };
  const source = readFileSync(
    path.resolve(__dirname, "../../catbot/ui/audio.js"),
    "utf8",
  );
  const { AudioController } = await import(
    "data:text/javascript;base64," + Buffer.from(source).toString("base64")
  );
  const audio = new AudioController((message) => events.push(message));
  await audio.ensureEnabled();
  assert.equal(audio.enabled, true);
  assert(
    messages.some((message) => message.type === "playback" && message.enabled),
  );
  await audio.play({
    speech_id: "live",
    audio: Buffer.from("RIFFtest").toString("base64"),
    text: "Billu",
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert(events.includes("wav-decoded"));
  assert(events.includes("wav-started"));
  assert(
    messages.some(
      (message) =>
        message.speech_id === "live" && message.status === "completed",
    ),
  );
  await audio.play({
    speech_id: "fake",
    text: "Billu bol raha hoon",
    audio: null,
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert(events.includes("system-speech"));
  assert(
    messages.some(
      (message) =>
        message.speech_id === "fake" && message.status === "completed",
    ),
  );
  audio.userMuted = true;
  await audio.setEnabled(false);
  await audio.ensureEnabled();
  assert.equal(audio.enabled, false, "Respect an explicit voice-off choice");
});
