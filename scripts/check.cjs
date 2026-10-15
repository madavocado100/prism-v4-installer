const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'rgb-audio-visualizer-v4.html'), 'utf8');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
assert.ok(scripts.length, 'App must contain inline JavaScript');
for (const [index, match] of scripts.entries()) {
  new vm.Script(match[1], { filename: `inline-script-${index}.js` });
}
const match = html.match(/const DEFAULTS = (\{[\s\S]*?\n\});/);
assert.ok(match, 'Built-in defaults must exist');
const defaults = JSON.parse(JSON.stringify(vm.runInNewContext(`(${match[1]})`)));
const exported = JSON.parse(fs.readFileSync(path.join(root, 'config/default.json'), 'utf8'));
assert.equal(exported.__prism, 'v4');
assert.equal(exported.__preset, 'hyperdrive');
assert.deepEqual(exported.cfg, defaults, 'Export must match fresh-start defaults exactly');
for (const file of ['prism-v4.sh', 'prism-system-audio.sh']) {
  assert.ok(fs.statSync(path.join(root, file)).mode & 0o111, `${file} must be executable`);
}
console.log(`PASS: JavaScript syntax, ${Object.keys(defaults).length} default settings, executable launchers`);
