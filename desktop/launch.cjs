const { spawn } = require("node:child_process");
const path = require("node:path");
const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;
const args = process.argv.slice(2);
const target = args.includes("--probe")
  ? path.join(__dirname, "probe.cjs")
  : path.resolve(__dirname, "..");
const child = spawn(
  require("electron"),
  [target, ...args.filter((arg) => arg !== "--probe")],
  { env, stdio: "inherit", windowsHide: false },
);
child.on("error", (error) => {
  console.error("Could not launch Catbot:", error.message);
  process.exitCode = 1;
});
child.on("exit", (code) => {
  process.exitCode = code ?? 1;
});
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => child.kill(signal));
