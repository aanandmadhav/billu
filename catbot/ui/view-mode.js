export async function setupViewMode() {
  const button = document.getElementById("view-mode");
  const stage = document.getElementById("cat-stage");
  const slot = document.getElementById("simple-feedback");
  const native = window.catbotDesktop;
  const movable = ["confirm-timer", "confirm-actions", "code"].map((id) => {
    const node = document.getElementById(id);
    const anchor = document.createComment(`${id} dashboard position`);
    node.before(anchor);
    return { node, anchor };
  });
  let simple = false;
  let revision = 0;
  function apply(mode) {
    simple = mode === "simple";
    if (
      simple &&
      document.getElementById("activity-pane").contains(document.activeElement)
    )
      button.focus();
    document.body.classList.toggle("simple-mode", simple);
    button.setAttribute("aria-pressed", String(simple));
    button.textContent = simple ? "Full dashboard" : "Simple mode";
    stage.setAttribute("aria-label", simple ? "Billu, simple mode" : "Billu");
    for (const { node, anchor } of movable) {
      if (simple) slot.append(node);
      else anchor.after(node);
    }
  }
  button.addEventListener("click", async () => {
    revision++;
    const mode = simple ? "dashboard" : "simple";
    apply(mode);
    try {
      if (native?.setViewMode) await native.setViewMode(mode);
      else localStorage.setItem("catbot-view-mode", mode);
    } catch {
      // Keep the selected view usable even if saving is unavailable.
    }
  });
  const initialRevision = revision;
  try {
    const mode = native?.getViewMode
      ? await native.getViewMode()
      : localStorage.getItem("catbot-view-mode");
    if (revision === initialRevision) apply(mode);
  } catch {
    if (revision === initialRevision) apply("dashboard");
  }
}
