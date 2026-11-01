const http = require("node:http");
const { randomBytes, timingSafeEqual } = require("node:crypto");

// Private transport for the gated Python screenshot tool. No renderer API,
// arbitrary command, output path, remote host or image upload is accepted.
async function startCaptureBridge({ desktopCapturer, screen, isFake }) {
  const token = randomBytes(32).toString("hex");
  const authorization = Buffer.from(`Bearer ${token}`);
  const server = http.createServer(async (request, response) => {
    const supplied = Buffer.from(request.headers.authorization || "");
    if (
      supplied.length !== authorization.length ||
      !timingSafeEqual(supplied, authorization)
    ) {
      response.writeHead(401).end();
      return;
    }
    if (
      request.method !== "POST" ||
      request.url !== "/capture" ||
      Number(request.headers["content-length"] || 0) !== 0 ||
      request.headers["transfer-encoding"]
    ) {
      response.writeHead(400).end();
      return;
    }
    if (isFake()) {
      response.writeHead(403).end();
      return;
    }
    let timer;
    try {
      const display = screen.getPrimaryDisplay();
      const size = {
        width: Math.min(
          8192,
          Math.ceil(display.size.width * display.scaleFactor),
        ),
        height: Math.min(
          8192,
          Math.ceil(display.size.height * display.scaleFactor),
        ),
      };
      const sources = await Promise.race([
        desktopCapturer.getSources({
          types: ["screen"],
          thumbnailSize: size,
          fetchWindowIcons: false,
        }),
        new Promise((_, reject) => {
          timer = setTimeout(
            () => reject(new Error("Capture timed out")),
            12000,
          );
        }),
      ]);
      const source =
        sources.find((item) => item.display_id === String(display.id)) ||
        sources[0];
      if (!source || source.thumbnail.isEmpty())
        throw new Error("No screen image");
      const png = source.thumbnail.toPNG();
      if (png.length > 50 * 1024 * 1024) throw new Error("Image too large");
      response.writeHead(200, {
        "Content-Type": "image/png",
        "Content-Length": png.length,
        "Cache-Control": "no-store",
      });
      response.end(png);
    } catch {
      response.writeHead(403, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ error: "screen_capture_failed" }));
    } finally {
      clearTimeout(timer);
    }
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  return {
    endpoint: `http://127.0.0.1:${server.address().port}/capture`,
    token,
    close: async () => {
      server.closeAllConnections();
      await new Promise((resolve) => server.close(resolve));
    },
  };
}
module.exports = { startCaptureBridge };
