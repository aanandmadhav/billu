export function setupPushToTalk({
  audio,
  button,
  label,
  input,
  notice,
  listening,
}) {
  let keyboardHeld = null;
  let pointerHeld = false;
  let intended = false;
  let revision = 0;
  function resetButton() {
    button.classList.remove("recording");
    delete button.dataset.pending;
    label.textContent = "Hold Space to talk";
  }
  audio.onStop = () => {
    intended = false;
    revision++;
    resetButton();
  };
  async function press() {
    if (intended) return;
    intended = true;
    const current = ++revision;
    button.dataset.pending = "true";
    label.textContent = "Opening microphone… keep holding";
    notice("Opening microphone… keep holding.");
    try {
      const started = await audio.start();
      if (current !== revision || !intended) return;
      delete button.dataset.pending;
      if (started) {
        button.classList.add("recording");
        label.textContent = "Bolo… release to send";
        if (!audio.fake) notice("");
        listening();
      } else {
        intended = false;
        resetButton();
      }
    } catch (error) {
      if (current !== revision) return;
      intended = false;
      resetButton();
      notice(error.message);
    }
  }
  async function release() {
    if (keyboardHeld || pointerHeld || !intended) return;
    intended = false;
    revision++;
    if (button.dataset.pending)
      notice("Recording cancelled. Press and hold until Billu is listening.");
    resetButton();
    try {
      await audio.stop();
    } catch (error) {
      notice(error.message);
    }
  }
  function keyboardCapture(event) {
    if (event.altKey || event.metaKey || event.ctrlKey || event.isComposing)
      return false;
    if (
      event.target?.closest?.(
        "input,textarea,select,[contenteditable]:not([contenteditable=false]),[role=textbox],dialog",
      )
    )
      return false;
    return (
      event.code === "Space" ||
      (event.code === "Enter" && button.contains(event.target))
    );
  }
  document.addEventListener(
    "keydown",
    (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        input.focus();
        return;
      }
      if (!keyboardCapture(event)) return;
      // Cancel the focused button's native Space click on both key events.
      event.preventDefault();
      event.stopPropagation();
      if (event.repeat || keyboardHeld) return;
      keyboardHeld = event.code;
      press();
    },
    true,
  );
  document.addEventListener(
    "keyup",
    (event) => {
      if (!keyboardHeld || event.code !== keyboardHeld) return;
      event.preventDefault();
      event.stopPropagation();
      keyboardHeld = null;
      release();
    },
    true,
  );
  button.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || event.isPrimary === false) return;
    event.preventDefault();
    pointerHeld = true;
    try {
      button.setPointerCapture(event.pointerId);
    } catch {}
    press();
  });
  for (const type of ["pointerup", "pointercancel", "lostpointercapture"])
    button.addEventListener(type, () => {
      pointerHeld = false;
      release();
    });
  window.addEventListener("blur", () => {
    keyboardHeld = null;
    pointerHeld = false;
    release();
  });
}
