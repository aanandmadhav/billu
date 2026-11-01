import { Resvg } from "@resvg/resvg-js";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
export async function buildIcon(root, staging) {
  const html = await readFile(path.join(root, "catbot/ui/index.html"), "utf8");
  let svg = html.match(/<svg id="cat"[\s\S]*?<\/svg>/)[0];
  const css = await readFile(path.join(root, "catbot/ui/tokens.css"), "utf8");
  const tokens = Object.fromEntries(
    [...css.matchAll(/(--c-[\w-]+):\s*([^;]+);/g)].map((match) => [
      match[1],
      match[2],
    ]),
  );
  tokens["--stage-color"] = tokens["--c-catnip"];
  tokens["--font-display"] = "Georgia";
  svg = svg.replace(
    /var\((--[\w-]+)\)/g,
    (_all, key) => tokens[key] || "currentColor",
  );
  svg = svg.replace(
    ' <g class="wave-ring"',
    ' <style>.eyes-open,.eyes-narrow,.eyes-happy,.orbit,.paw-stop,.sparkle,.wave-ring,.tape,.zzz{display:none}</style><g class="wave-ring"',
  );
  const png = new Resvg(svg, {
    fitTo: { mode: "width", value: 1024 },
    font: { loadSystemFonts: false },
  })
    .render()
    .asPng();
  const pngPath = path.join(staging, "Catbot.png");
  await writeFile(pngPath, png);
  if (process.platform !== "darwin") return pngPath;
  const directory = path.join(staging, "Catbot.iconset");
  await mkdir(directory, { recursive: true });
  for (const size of [16, 32, 128, 256, 512]) {
    for (const scale of [1, 2]) {
      const target = path.join(
        directory,
        `icon_${size}x${size}${scale === 2 ? "@2x" : ""}.png`,
      );
      const image = new Resvg(svg, {
        fitTo: { mode: "width", value: size * scale },
        font: { loadSystemFonts: false },
      })
        .render()
        .asPng();
      await writeFile(target, image);
    }
  }
  const icon = path.join(staging, "Catbot.icns");
  await promisify(execFile)("/usr/bin/iconutil", [
    "-c",
    "icns",
    directory,
    "-o",
    icon,
  ]);
  return icon;
}
