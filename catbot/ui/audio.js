// Shared browser/Electron audio. Speech completion is acknowledged before Billu mutes.
export class AudioController {
  constructor(notice) {
    Object.assign(this, {
      notice,
      enabled: false,
      fake: null,
      context: null,
      socket: null,
      playing: null,
      speech: null,
      reconnect: 1000,
      disposed: false,
      recording: false,
      stream: null,
      worklet: null,
      source: null,
      onLevel: null,
      onStop: null,
      onState: null,
      flushed: null,
      userMuted: false,
      captureEpoch: 0,
      stopping: false,
    });
    this.connect();
  }
  control(message) {
    if (this.socket?.readyState === WebSocket.OPEN)
      this.socket.send(JSON.stringify(message));
  }
  connect() {
    if (this.disposed) return;
    this.socket = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/audio`,
    );
    this.socket.onopen = () => {
      this.reconnect = 1000;
      this.control({ type: "playback", enabled: this.enabled });
    };
    this.socket.onmessage = async (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }
      if (data.type === "tts") await this.play(data);
      if (data.type === "error") {
        this.notice(data.message);
        if (data.stop_recording) await this.stop();
      }
    };
    this.socket.onclose = () => {
      this.stopPlayback();
      this.cleanupCapture();
      if (!this.disposed) setTimeout(() => this.connect(), this.reconnect);
      this.reconnect = Math.min(this.reconnect * 2, 8000);
    };
  }
  async ready() {
    for (let i = 0; i < 60; i++) {
      if (this.socket?.readyState === WebSocket.OPEN) return;
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    throw new Error("Billu’s audio connection is unavailable. Try again.");
  }
  async setEnabled(enabled) {
    if (enabled) {
      this.context ??= new AudioContext();
      await this.context.resume();
      if (this.context.state !== "running")
        throw new Error("Audio is blocked. Click Voice on to allow playback.");
    }
    this.enabled = enabled;
    this.control({ type: "playback", enabled });
    if (!enabled) this.stopPlayback();
    this.onState?.(enabled ? "ready" : "off");
    return enabled;
  }
  async ensureEnabled() {
    if (!this.enabled && !this.userMuted) await this.setEnabled(true);
  }
  async enable() {
    this.userMuted = this.enabled;
    return this.setEnabled(!this.enabled);
  }
  ack(id, status = "completed", provider = null) {
    this.control({ type: "played", speech_id: id, status, provider });
  }
  async play(data) {
    if (!this.enabled || this.recording) {
      this.ack(data.speech_id, "interrupted");
      return;
    }
    this.stopPlayback();
    const speech = {
      id: data.speech_id,
      finished: false,
      provider: data.audio ? "sarvam" : "system",
    };
    speech.finish = (status) => {
      if (speech.finished) return;
      speech.finished = true;
      this.ack(speech.id, status, speech.provider);
      this.onState?.(
        status === "failed" ? "failed" : this.enabled ? "ready" : "off",
      );
      if (this.speech === speech) this.speech = null;
    };
    this.speech = speech;
    try {
      if (!data.audio) {
        this.speakLocal(data.text, speech);
        return;
      }
      await this.context.resume();
      if (this.context.state !== "running") throw new Error("Audio suspended");
      const bytes = Uint8Array.from(atob(data.audio), (c) => c.charCodeAt(0));
      const buffer = await this.context.decodeAudioData(bytes.buffer);
      if (this.recording || speech.finished) {
        speech.finish("interrupted");
        return;
      }
      const source = this.context.createBufferSource();
      source.buffer = buffer;
      source.connect(this.context.destination);
      this.playing = source;
      source.onended = () => {
        if (this.playing === source) this.playing = null;
        speech.finish("completed");
      };
      this.onState?.("speaking");
      source.start();
    } catch {
      if (data.text && !speech.finished) {
        this.notice(
          "Sarvam audio could not play. Billu is using the system voice.",
        );
        this.speakLocal(data.text, speech);
      } else {
        speech.finish("failed");
        this.notice("Voice playback failed. Check your sound output.");
      }
    }
  }
  speakLocal(text, speech) {
    speech.provider = "system";
    if (!text || !("speechSynthesis" in window)) {
      speech.finish("failed");
      this.notice(
        "System speech is unavailable. Use live mode for Sarvam voice.",
      );
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    const voices = speechSynthesis.getVoices();
    utterance.voice =
      voices.find(
        (voice) => voice.localService && voice.lang.startsWith("hi"),
      ) ||
      voices.find(
        (voice) => voice.localService && voice.lang.startsWith("en"),
      ) ||
      null;
    utterance.lang = utterance.voice?.lang || "hi-IN";
    utterance.rate = 1.05;
    utterance.onend = () => speech.finish("completed");
    utterance.onerror = () => {
      speech.finish("failed");
      this.notice("System speech failed. Check your audio output.");
    };
    this.onState?.("system-speaking");
    speechSynthesis.speak(utterance);
  }
  stopPlayback() {
    if (this.speech) this.speech.finish("interrupted");
    if (this.playing) {
      try {
        this.playing.stop();
      } catch {}
      this.playing = null;
    }
    if ("speechSynthesis" in window) speechSynthesis.cancel();
  }
  async start() {
    if (this.stopping) {
      this.notice("Finishing the last recording. Press and hold again.");
      return false;
    }
    if (this.recording) return false;
    const captureEpoch = ++this.captureEpoch;
    if (this.fake === null) {
      this.notice("Connecting to Billu. Try again in a moment.");
      return false;
    }
    await this.ensureEnabled();
    if (captureEpoch !== this.captureEpoch) return false;
    this.stopPlayback();
    this.control({ type: "interrupt" });
    if (this.recording) return false;
    if (this.socket?.readyState !== WebSocket.OPEN) {
      this.notice("Audio is reconnecting. Type your command for now.");
      return false;
    }
    this.recording = true;
    if (this.fake) {
      this.control({ type: "start" });
      this.notice(
        "Fake microphone: release to run a demo command. No microphone is accessed.",
      );
      return true;
    }
    try {
      this.context ??= new AudioContext();
      await this.context.resume();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      if (!this.recording || captureEpoch !== this.captureEpoch) {
        stream.getTracks().forEach((track) => track.stop());
        return false;
      }
      this.stream = stream;
      if (!this.workletLoaded) {
        await this.context.audioWorklet.addModule("/ui/pcm-worklet.js");
        this.workletLoaded = true;
      }
      if (!this.recording || captureEpoch !== this.captureEpoch) {
        stream.getTracks().forEach((track) => track.stop());
        if (this.stream === stream) this.cleanupCapture();
        return false;
      }
      this.source = this.context.createMediaStreamSource(stream);
      this.worklet = new AudioWorkletNode(this.context, "billu-pcm");
      this.worklet.port.onmessage = (event) => {
        if (captureEpoch !== this.captureEpoch) return;
        const data = event.data;
        if (data.pcm && this.socket?.readyState === WebSocket.OPEN) {
          if (this.socket.bufferedAmount > 32000 * 5) {
            this.notice("Voice connection is too slow. Release and try again.");
            this.stop();
            return;
          }
          this.socket.send(data.pcm);
          this.onLevel?.(data.level);
        }
        if (data.final && this.flushed) {
          this.flushed();
          this.flushed = null;
        }
      };
      this.worklet.onprocessorerror = () => {
        if (captureEpoch !== this.captureEpoch) return;
        this.notice("Microphone processing stopped. Release and try again.");
        this.stop();
      };
      for (const track of stream.getTracks())
        track.onended = () => {
          if (captureEpoch !== this.captureEpoch) return;
          this.notice(
            "The microphone disconnected. Reconnect it and try again.",
          );
          this.stop();
        };
      this.control({ type: "start" });
      this.source.connect(this.worklet);
      this.worklet.connect(this.context.destination);
      this.maxTimer = setTimeout(() => this.stop(), 30000);
      return true;
    } catch (error) {
      if (captureEpoch !== this.captureEpoch) return false;
      this.recording = false;
      this.cleanupCapture();
      const messages = {
        NotAllowedError: window.catbotDesktop
          ? "Microphone access is blocked. In Full dashboard, open Permissions, then Enable microphone. Restart Catbot after granting access."
          : "Microphone access is blocked. Allow it in your browser's site settings, then try again.",
        NotFoundError:
          "No microphone was found. Connect one and check System Settings → Sound → Input.",
        NotReadableError:
          "The microphone is unavailable. Check your selected sound input and close any app holding it.",
      };
      this.notice(
        messages[error.name] ||
          "The microphone could not start. Check your sound input, or type below.",
      );
      return false;
    }
  }
  async stop() {
    if (this.stopping) return;
    if (!this.recording) {
      this.captureEpoch++;
      return;
    }
    this.stopping = true;
    this.recording = false;
    clearTimeout(this.maxTimer);
    try {
      if (this.worklet)
        await new Promise((resolve) => {
          this.flushed = resolve;
          this.worklet.port.postMessage({ type: "flush" });
          setTimeout(resolve, 250);
        });
    } finally {
      this.cleanupCapture();
      this.control({ type: "stop" });
      this.onLevel?.(0);
      this.stopping = false;
    }
  }
  cleanupCapture() {
    this.captureEpoch++;
    clearTimeout(this.maxTimer);
    this.source?.disconnect();
    this.worklet?.disconnect();
    if (this.worklet) {
      this.worklet.port.onmessage = null;
      this.worklet.port.close();
    }
    this.flushed = null;
    this.source = null;
    this.worklet = null;
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    this.recording = false;
    this.onStop?.();
  }
  sound(kind) {
    if (!this.enabled || !this.context) return;
    const ctx = this.context,
      start = ctx.currentTime,
      oscillator = ctx.createOscillator(),
      gain = ctx.createGain();
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    const tones = {
      purr: [75, 90, 0.45],
      snore: [53, 41, 0.65],
      growl: [80, 45, 0.35],
      suspense: [185, 196, 0.35],
      slurp: [240, 80, 0.25],
      hiss: [540, 230, 0.18],
      dhol: [160, 50, 0.24],
      horn: [310, 280, 0.2],
    };
    const [a, b, d] = tones[kind] || tones.purr;
    oscillator.type = kind === "hiss" ? "sawtooth" : "sine";
    oscillator.frequency.setValueAtTime(a, start);
    oscillator.frequency.exponentialRampToValueAtTime(b, start + d);
    gain.gain.setValueAtTime(0.045, start);
    gain.gain.exponentialRampToValueAtTime(0.001, start + d);
    oscillator.start(start);
    oscillator.stop(start + d);
  }
}
