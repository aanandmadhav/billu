const fs = require("node:fs");
const path = require("node:path");

function viewPreferences(userData) {
  const file = path.join(userData, "view-mode.json");
  return {
    get() {
      try {
        return JSON.parse(fs.readFileSync(file, "utf8")).mode === "simple"
          ? "simple"
          : "dashboard";
      } catch {
        return "dashboard";
      }
    },
    set(mode) {
      if (!["simple", "dashboard"].includes(mode))
        throw new Error("Unknown view mode.");
      fs.mkdirSync(userData, { recursive: true });
      fs.writeFileSync(file, JSON.stringify({ mode }));
      return mode;
    },
  };
}
module.exports = { viewPreferences };
