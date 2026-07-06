// Cloudflare Pages serves build/404.html (with a 404 status) for unmatched
// routes; without it, every bad URL gets the homepage as a 200. Evidence
// prerenders pages/404.md to build/404/index.html, so lift a copy to the root.
import { copyFileSync } from 'node:fs';

copyFileSync('build/404/index.html', 'build/404.html');
console.log('copy-404: build/404/index.html -> build/404.html');
