export async function setupDesktop(audio, notice) {
  const native = window.catbotDesktop;
  const voice = document.getElementById("voice-toggle");
  const status = document.getElementById("voice-status");
  audio.onState = (state) => {
    voice.textContent = audio.enabled ? "Voice on" : "Voice off";
    voice.setAttribute("aria-pressed", String(audio.enabled));
    status.textContent =
      {
        ready: "Voice ready",
        off: "Voice off",
        speaking: "Billu is speaking…",
        "system-speaking": "Billu is speaking · system voice",
        failed: "Voice failed: try Test voice",
      }[state] || state;
  };
  document
    .getElementById("test-voice")
    .addEventListener("click", async (event) => {
      event.currentTarget.disabled = true;
      try {
        audio.userMuted = false;
        await audio.setEnabled(true);
        await audio.ready();
        const response = await fetch("/api/voice/test", { method: "POST" });
        if (!response.ok) {
          const body = await response.json();
          throw new Error(body.detail);
        }
      } catch (error) {
        notice(error.message);
      } finally {
        document.getElementById("test-voice").disabled = false;
      }
    });
  if (!native) {
    status.textContent = "Voice starts when you send a command";
    return;
  }
  document.body.classList.add("desktop-app");
  const panel = document.getElementById("desktop-setup");
  panel.hidden = false;
  document.getElementById("permissions-open").hidden = false;
  document.getElementById("permissions-open").onclick = () => {
    panel.hidden = !panel.hidden;
  };
  async function refresh() {
    const permissions = await native.permissions();
    for (const [id, value] of [
      ["mic-status", permissions.microphone],
      ["screen-status", permissions.screen],
      ["accessibility-status", permissions.accessibility],
    ]) {
      const element = document.getElementById(id);
      element.textContent =
        {
          granted: "Ready",
          demo: "Demo mode",
          denied: "Allow in System Settings",
          restricted: "Restricted by system",
          "not-granted": "Needs permission",
          "not-determined": "Needs permission",
          "not-required": "Not required",
          "request-on-use": "Requested when you talk",
        }[value] || "Check permissions";
      element.style.color = `var(--c-${value === "granted" ? "catnip" : value === "denied" ? "chili" : "muted"})`;
    }
    const volume = await native
      .volumeStatus()
      .catch(() => ({ available: false }));
    document.getElementById("restore-sound").hidden = !(
      volume.muted || volume.level === 0
    );
    document.getElementById("output-status").textContent = volume.demo
      ? "Demo output"
      : volume.muted || volume.level === 0
        ? "System output is muted. Say “volume wapas karo” to restore it."
        : volume.available
          ? `System output: ${volume.level}%`
          : "Check your selected system sound output.";
    return permissions;
  }
  let demo = true,
    permissionRequestActive = false;
  async function advancePermissions() {
    if (demo || native.smoke || permissionRequestActive) return;
    permissionRequestActive = true;
    try {
      const current = await native.permissions();
      if (!current.firstRun || current.microphone !== "granted") return;
      if (current.accessibility === "not-granted")
        await native.requestPermission("accessibility");
      await native.completeSetup();
      await refresh();
    } finally {
      permissionRequestActive = false;
    }
  }
  for (const kind of ["microphone", "accessibility", "screen"]) {
    document.getElementById(`allow-${kind}`).onclick = async () => {
      try {
        await native.requestPermission(kind);
        await refresh();
        if (kind === "microphone") await advancePermissions();
      } catch (error) {
        notice(error.message);
      }
    };
  }
  document.getElementById("restore-sound").onclick = async () => {
    try {
      await audio.ensureEnabled();
      const response = await fetch("/api/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ utterance: "volume wapas karo" }),
      });
      if (!response.ok)
        throw new Error("Billu is busy. Try restoring sound again.");
      notice("Billu is restoring sound through the safety gate.");
      setTimeout(() => refresh().catch(() => {}), 2000);
    } catch (error) {
      notice(error.message);
    }
  };
  document.getElementById("permissions-refresh").onclick = () =>
    refresh().catch((error) => notice(error.message));
  document.getElementById("permissions-done").onclick = () => {
    panel.hidden = true;
    document.getElementById("utterance").focus();
  };
  window.addEventListener("focus", () =>
    refresh()
      .then(advancePermissions)
      .catch(() => {}),
  );
  try {
    await audio.setEnabled(true);
    await audio.ready();
    const permissions = await refresh();
    const response = await fetch("/api/stats");
    const stats = await response.json();
    demo = stats.fake;
    if (!stats.fake && !native.smoke && permissions.firstRun) {
      if (permissions.microphone !== "granted")
        await native.requestPermission("microphone");
      await advancePermissions();
    }
    const greeting = await fetch("/api/voice/test", { method: "POST" });
    if (!greeting.ok)
      notice("Click Test voice to hear Billu. Restore system volume if muted.");
  } catch (error) {
    notice(error.message);
  }
}
