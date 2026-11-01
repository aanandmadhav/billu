import { packager } from "@electron/packager";
import { buildIcon } from "./icon.mjs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { mkdir, writeFile } from "node:fs/promises";
import { existsSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const staging = path.join(root, ".desktop-build");
await mkdir(staging, { recursive: true });
const projectFile = path.join(staging, "project.json");
await writeFile(projectFile, JSON.stringify({ root }));
const archive = path.join(staging, "electron-v45.2.1-darwin-arm64.zip");
let archiveOptions = {};
if (
  process.platform === "darwin" &&
  process.arch === "arm64" &&
  existsSync(archive)
) {
  const expected = JSON.parse(
    readFileSync(
      path.join(root, "node_modules/electron/checksums.json"),
      "utf8",
    ),
  )[path.basename(archive)];
  if (
    createHash("sha256").update(readFileSync(archive)).digest("hex") !==
    expected
  )
    throw new Error(
      "The local Electron download is incomplete or has an invalid checksum.",
    );
  archiveOptions = { electronZipDir: staging };
}
const icon = await buildIcon(root, staging);
const bundles = await packager({
  icon,
  dir: root,
  name: "Catbot",
  appBundleId: "dev.hacksmith.catbot",
  // Local development identity: seal the renamed bundle and its helpers after
  // packaging so macOS sees Catbot, rather than the original Electron linker ID.
  ...(process.platform === "darwin"
    ? {
        osxSign: {
          identity: "-",
          identityValidation: false,
          preAutoEntitlements: false,
          preEmbedProvisioningProfile: false,
          optionsForFile: () => ({ hardenedRuntime: false, timestamp: "none" }),
        },
      }
    : {}),
  appVersion: "0.1.0",
  out: path.join(root, "dist"),
  overwrite: true,
  asar: true,
  ignore: [
    /^\/(?:\.git|\.venv|\.env(?:\.|$)|models|assets|sandbox|catbot|tests|scripts|docs|dist|\.desktop-build)(?:\/|$)/,
  ],
  extraResource: [projectFile],
  ...archiveOptions,
  extendInfo: {
    NSMicrophoneUsageDescription:
      "Billu listens to your spoken commands only while you hold the talk button.",
    NSAppleEventsUsageDescription:
      "Billu uses approved desktop actions requested by you.",
    NSHumanReadableCopyright: "Hacksmith · Catbot, starring Billu",
  },
  usageDescription: {
    Microphone: "Billu listens while you hold the talk button.",
  },
});
if (process.platform === "darwin") {
  for (const directory of bundles) {
    const bundle = path.join(directory, "Catbot.app");
    await promisify(execFile)("/usr/bin/codesign", [
      "--verify",
      "--deep",
      "--strict",
      bundle,
    ]);
    const { stderr } = await promisify(execFile)("/usr/bin/codesign", [
      "-dv",
      "--verbose=2",
      bundle,
    ]);
    if (!stderr.includes("Identifier=dev.hacksmith.catbot\n"))
      throw new Error(
        "Packaged app does not have the Catbot signing identity.",
      );
  }
}
console.log(bundles.join("\n"));
