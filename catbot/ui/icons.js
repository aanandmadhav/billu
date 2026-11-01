// Local SVG paths: quiet functional marks, no icon containers or runtime CDN.
const paths={
 listen:'<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8"/>',
 think:'<path d="M12 18V5m0 0c-4-5-10 1-6 4-6 2-2 10 2 8 0 5 4 5 4 1m0-13c4-5 10 1 6 4 6 2 2 10-2 8 0 5-4 5-4 1"/>',
 risk:'<path d="M3 18a10 10 0 1 1 18 0M12 13l5-5"/><circle cx="12" cy="13" r="2"/>',
 gate:'<path d="M12 3 3 7v6c0 5 9 9 9 9s9-4 9-9V7z"/>',
 confirm:'<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 5 2c-2 1-2 2-2 3m0 3h.01"/>',
 execute:'<path d="m13 2-9 12h7l-1 8 10-12h-8z"/>',
 result:'<path d="m3 6 2 2 3-4m-5 9 2 2 3-4m4-5h9m-9 9h9M3 21h18"/>',
 speak:'<path d="m11 5-6 4H2v6h3l6 4zM15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/>',
 allow:'<path d="m5 12 4 4L20 5"/>',
 deny:'<path d="M12 3 3 7v6c0 5 9 9 9 9s9-4 9-9V7zM9 10l6 6m0-6-6 6"/>',
 send:'<path d="m5 17 13-13M7 4h11v11"/>',
 chai:'<path d="M4 8h12l-1 12H5zM16 10h2a3 3 0 0 1 0 6h-2M7 5V2m5 3V2"/>',
};
export function icon(name){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||paths.gate}</svg>`}
