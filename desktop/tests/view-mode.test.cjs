const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { viewPreferences } = require("../view-preferences.cjs");

test("view preference survives a new session and rejects unsupported values", () => {
  const sandbox = path.resolve(__dirname, "../../sandbox");
  fs.mkdirSync(sandbox, { recursive: true });
  const directory = fs.mkdtempSync(path.join(sandbox, "view-test-"));
  try {
    const first = viewPreferences(directory);
    assert.equal(first.get(), "dashboard");
    first.set("simple");
    assert.equal(viewPreferences(directory).get(), "simple");
    assert.throws(() => first.set("../other"), /Unknown view mode/);
    assert.equal(first.get(), "simple");
    fs.writeFileSync(path.join(directory, "view-mode.json"), "broken");
    assert.equal(first.get(), "dashboard");
  } finally {
    fs.rmSync(directory, { recursive: true });
  }
});

test("simple mode preserves live confirmation controls and restores their dashboard positions", async () => {
  class Element {
    constructor(id) {
      this.id = id;
      this.children = [];
      this.listeners = {};
      this.attributes = {};
    }
    append(node) {
      if (node.parent)
        node.parent.children.splice(node.parent.children.indexOf(node), 1);
      this.children.push(node);
      node.parent = this;
    }
    before(node) {
      this.parent.children.splice(this.parent.children.indexOf(this), 0, node);
      node.parent = this.parent;
    }
    after(node) {
      if (node.parent)
        node.parent.children.splice(node.parent.children.indexOf(node), 1);
      this.parent.children.splice(
        this.parent.children.indexOf(this) + 1,
        0,
        node,
      );
      node.parent = this.parent;
    }
    contains(node) {
      return (
        this === node || this.children.some((child) => child.contains(node))
      );
    }
    focus() {
      document.activeElement = this;
    }
    setAttribute(key, value) {
      this.attributes[key] = value;
    }
    addEventListener(key, callback) {
      this.listeners[key] = callback;
    }
  }
  const nodes = new Map();
  const get = (id) => {
    if (!nodes.has(id)) nodes.set(id, new Element(id));
    return nodes.get(id);
  };
  const pane = get("activity-pane"),
    verdict = get("verdict");
  pane.append(verdict);
  verdict.append(get("confirm-timer"));
  verdict.append(get("confirm-actions"));
  pane.append(get("code"));
  get("confirm-actions").hidden = false;
  get("confirm-actions").listeners.click = () => "approved";
  const classes = new Set(),
    saved = [];
  global.document = {
    getElementById: get,
    createComment: () => new Element(),
    activeElement: get("confirm-actions"),
    body: {
      classList: {
        toggle: (name, active) =>
          active ? classes.add(name) : classes.delete(name),
      },
    },
  };
  global.window = {
    catbotDesktop: {
      getViewMode: async () => "simple",
      setViewMode: async (mode) => saved.push(mode),
    },
  };
  const source = fs.readFileSync(
    path.resolve(__dirname, "../../catbot/ui/view-mode.js"),
    "utf8",
  );
  const { setupViewMode } = await import(
    "data:text/javascript;base64," + Buffer.from(source).toString("base64")
  );
  await setupViewMode();
  assert(classes.has("simple-mode"));
  assert.equal(document.activeElement, get("view-mode"));
  assert.equal(get("view-mode").attributes["aria-pressed"], "true");
  assert.equal(get("confirm-actions").parent, get("simple-feedback"));
  assert.equal(get("confirm-actions").hidden, false);
  assert.equal(get("confirm-actions").listeners.click(), "approved");
  assert.equal(get("code").parent, get("simple-feedback"));
  await get("view-mode").listeners.click();
  assert(!classes.has("simple-mode"));
  assert.equal(get("confirm-actions").parent, verdict);
  assert.equal(get("code").parent, pane);
  assert.deepEqual(saved, ["dashboard"]);
  await get("view-mode").listeners.click();
  assert.deepEqual(saved, ["dashboard", "simple"]);
});
