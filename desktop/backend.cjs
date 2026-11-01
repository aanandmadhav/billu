const { spawn } = require("node:child_process");
const { existsSync, readFileSync } = require("node:fs");
const path = require("node:path");
const { randomBytes } = require("node:crypto");

function projectRoot(resourcesPath, packaged) {
  const root =
    process.env.CATBOT_PROJECT_DIR ||
    (packaged
      ? JSON.parse(
          readFileSync(path.join(resourcesPath, "project.json"), "utf8"),
        ).root
      : path.resolve(__dirname, ".."));
  if (!existsSync(path.join(root, "catbot", "__main__.py")))
    throw new Error(
      "Catbot project not found. Set CATBOT_PROJECT_DIR to your checkout.",
    );
  return root;
}
function pythonPath(root) {
  const python =
    process.env.CATBOT_PYTHON ||
    path.join(
      root,
      ".venv",
      process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
    );
  if (!existsSync(python))
    throw new Error(
      'Python environment missing. Run uv venv and uv pip install -e ".[dev]" in the Catbot project.',
    );
  return python;
}
async function startBackend(root, fake) {
  const token = randomBytes(32).toString("hex");
  const env = {
    ...process.env,
    CATBOT_DESKTOP_TOKEN: token,
    PYTHONUNBUFFERED: "1",
  };
  delete env.ELECTRON_RUN_AS_NODE;
  const child = spawn(
    pythonPath(root),
    ["-m", "catbot", "--desktop", ...(fake ? ["--fake"] : [])],
    {
      cwd: root,
      env,
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  let stopped = false;
  const stop = async () => {
    if (stopped || child.exitCode !== null) return;
    stopped = true;
    child.kill("SIGTERM");
    await Promise.race([
      new Promise((resolve) => child.once("exit", resolve)),
      new Promise((resolve) => setTimeout(resolve, 4000)),
    ]);
    if (child.exitCode === null) child.kill("SIGKILL");
  };
  try {
    const port = await new Promise((resolve, reject) => {
      let buffered = "";
      const timeout = setTimeout(
        () =>
          reject(new Error("Billu’s backend did not start within 30 seconds.")),
        30000,
      );
      const fail = () => {
        clearTimeout(timeout);
        reject(
          new Error(
            "Billu’s Python backend stopped during startup. Check the Python environment.",
          ),
        );
      };
      child.once("error", fail);
      child.once("exit", fail);
      child.stderr.on("data", () => {}); // Drain; never copy service diagnostics or secrets into renderer logs.
      child.stdout.on("data", (block) => {
        buffered += block.toString();
        if (buffered.length > 16384) buffered = buffered.slice(-16384);
        for (const line of buffered.split("\n").slice(0, -1)) {
          if (!line.startsWith("CATBOT_READY ")) continue;
          try {
            const data = JSON.parse(line.slice(13));
            if (
              !Number.isInteger(data.port) ||
              data.port < 1 ||
              data.port > 65535
            )
              continue;
            clearTimeout(timeout);
            child.removeListener("exit", fail);
            child.removeListener("error", fail);
            resolve(data.port);
          } catch {}
        }
        buffered = buffered.split("\n").at(-1);
      });
    });
    const origin = `http://127.0.0.1:${port}`;
    for (let attempt = 0; attempt < 100; attempt++) {
      if (child.exitCode !== null)
        throw new Error("Billu’s backend exited before it became ready.");
      try {
        const response = await fetch(`${origin}/api/stats`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: AbortSignal.timeout(500),
        });
        if (response.ok) {
          const stats = await response.json();
          return { child, origin, token, stop, fake: stats.fake };
        }
      } catch {}
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    throw new Error("Billu’s backend could not be reached.");
  } catch (error) {
    await stop();
    throw error;
  }
}
module.exports = { startBackend, projectRoot, pythonPath };
