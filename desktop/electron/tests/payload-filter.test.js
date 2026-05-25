const assert = require('assert');
const path = require('path');

const full = require('../scripts/prepare-payload.js');
const lite = require('../scripts/prepare-payload-lite.js');

const repoRoot = path.resolve(__dirname, '..', '..', '..');

function p(relPath) {
    return path.join(repoRoot, relPath);
}

for (const [name, mod] of [['full', full], ['lite', lite]]) {
    assert.strictEqual(mod.shouldSkip(p('app/config/.env')), true, `${name}: .env must be skipped`);
    assert.strictEqual(mod.shouldSkip(p('app/config/.env_dev')), true, `${name}: .env_dev must be skipped`);
    assert.strictEqual(mod.shouldSkip(p('app/config/.env.production')), true, `${name}: .env.production must be skipped`);
    assert.strictEqual(mod.shouldSkip(p('app/config/.env.example')), false, `${name}: .env.example must ship`);
    assert.strictEqual(mod.shouldSkip(p('app/config/client.pem')), true, `${name}: cert/key files must be skipped`);
    assert.strictEqual(mod.shouldSkip(p('app/config/service-account-token.json')), true, `${name}: token files must be skipped`);
    assert.strictEqual(mod.shouldSkip(p('app/config/private_key.json')), true, `${name}: private-key files must be skipped`);
}

console.log('payload filter tests passed');

