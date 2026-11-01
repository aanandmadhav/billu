function trustedPage(url, origin) {
  try {
    const target = new URL(url);
    return target.origin === origin && target.pathname === "/";
  } catch {
    return false;
  }
}
function allowedPermission(permission, details = {}) {
  return (
    permission === "media" &&
    Array.isArray(details.mediaTypes) &&
    details.mediaTypes.length > 0 &&
    details.mediaTypes.every((type) => type === "audio")
  );
}
function previewPrefix(url, origin) {
  try {
    const target = new URL(url);
    return target.origin === origin &&
      /^\/apps\/[a-f0-9]{32}\//.test(target.pathname)
      ? `${origin}${target.pathname.match(/^\/apps\/[a-f0-9]{32}\//)[0]}`
      : null;
  } catch {
    return null;
  }
}
module.exports = { trustedPage, allowedPermission, previewPrefix };
