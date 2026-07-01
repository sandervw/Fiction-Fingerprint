// Cloudflare Pages caps files at 25 MiB; the bundled DuckDB-WASM binaries exceed it.
// Rewrite their URLs to the identical files on jsDelivr and drop them from the build.
import { readFileSync, writeFileSync, readdirSync, rmSync } from 'node:fs';
import { join } from 'node:path';

const version = JSON.parse(
	readFileSync('node_modules/@duckdb/duckdb-wasm/package.json', 'utf8')
).version;
const cdn = `https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@${version}/dist`;

const assetsDir = 'build/_app/immutable/assets';
const wasmFiles = readdirSync(assetsDir).filter(
	(f) => f.startsWith('duckdb-') && f.endsWith('.wasm')
);

const jsFiles = [];
(function walk(dir) {
	for (const entry of readdirSync(dir, { withFileTypes: true })) {
		const path = join(dir, entry.name);
		if (entry.isDirectory()) walk(path);
		else if (entry.name.endsWith('.js')) jsFiles.push(path);
	}
})('build');

for (const wasm of wasmFiles) {
	const bundledUrl = `/_app/immutable/assets/${wasm}`;
	const cdnUrl = `${cdn}/${wasm.split('.')[0]}.wasm`;
	let patched = 0;
	for (const js of jsFiles) {
		const src = readFileSync(js, 'utf8');
		if (!src.includes(bundledUrl)) continue;
		writeFileSync(js, src.replaceAll(bundledUrl, cdnUrl));
		patched++;
	}
	if (patched === 0) throw new Error(`no JS reference found for ${wasm}`);
	rmSync(join(assetsDir, wasm));
	console.log(`cdn-wasm: ${wasm} -> ${cdnUrl} (${patched} file(s) patched)`);
}
