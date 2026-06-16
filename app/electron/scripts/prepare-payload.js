/* prepare-payload.js
 *
 * Stages everything the offline installer must ship into
 *   app/electron/payload/
 *
 * What goes in:
 *   - services/, app/config|src|scripts|requirements|image_pipeline|configs_vps|rag/,
 *     ComfyUI/, app/storage/ (curated), LORA/ (filtered), root requirements*.txt
 *   - app/config/.env.example  (real .env files are provisioned on install)
 *   - python311/  (portable Python runtime; user provides per PACKAGING.md)
 *   - wheels/core/ + wheels/image/  (offline pip cache; user pre-downloads)
 *   - scripts/setup_venvs.py  (postinstall venv bootstrap)
 *
 * What is excluded:
 *   - venv-core/, venv-image/  (will be rebuilt on the target machine)
 *   - __pycache__, .git*, *.pyc, *.log, node_modules/, real .env files,
 *     keys/certs/credential-like files
 *   - ComfyUI/output|temp|user, app/logs|local_data|uploads|storage outputs, logs/, tmp/
 *   - private/, app/character_select_stand_alone_app-main/ (sidecars, opt-in later)
 *
 * Run:
 *   node scripts/prepare-payload.js
 */
const fs   = require('fs-extra');
const path = require('path');

const ELECTRON_DIR = path.resolve(__dirname, '..');
const REPO_ROOT    = path.resolve(ELECTRON_DIR, '..', '..');
const PAYLOAD      = path.join(ELECTRON_DIR, 'payload');

// Items copied verbatim. Each entry: { src (rel to repo root), dst (rel to payload), required }
const COPY_ITEMS = [
    { src: 'services',                                        dst: 'services',                                        required: true  },
    { src: 'app/config',                                      dst: 'app/config',                                      required: true  },
    { src: 'app/src',                                         dst: 'app/src',                                         required: true  },
    { src: 'app/scripts',                                     dst: 'app/scripts',                                     required: false },
    { src: 'app/requirements',                                dst: 'app/requirements',                                required: true  },
    { src: 'ComfyUI',                                         dst: 'ComfyUI',                                         required: true  },
    { src: 'app/image_pipeline',                              dst: 'app/image_pipeline',                              required: true  },
    { src: 'app/configs_vps',                                 dst: 'app/configs_vps',                                 required: true  },
    { src: 'app/rag',                                         dst: 'app/rag',                                         required: false },
    { src: 'app/storage/character_db',                        dst: 'app/storage/character_db',                        required: false },
    { src: 'app/storage/character_loras',                     dst: 'app/storage/character_loras',                     required: false },
    { src: 'app/storage/character_refs',                      dst: 'app/storage/character_refs',                      required: false },
    { src: 'app/storage/feature_layers',                      dst: 'app/storage/feature_layers',                      required: false },
    { src: 'app/storage/metadata',                            dst: 'app/storage/metadata',                            required: false },
    { src: 'app/storage/prompts',                             dst: 'app/storage/prompts',                             required: false },
    { src: 'app/storage/references',                          dst: 'app/storage/references',                          required: false },
    { src: 'app/storage/lora_inventory.json',                 dst: 'app/storage/lora_inventory.json',                 required: false },
    { src: 'LORA',                                            dst: 'LORA',                                            required: false },
    { src: 'requirements.txt',                                dst: 'requirements.txt',                                required: false },
    { src: 'requirements-core.txt',                           dst: 'requirements-core.txt',                           required: false },
    { src: 'requirements-image.txt',                          dst: 'requirements-image.txt',                          required: false },
];

// Path-based exclusion. Tested as substring against forward-slash relative path.
const EXCLUDE_SUBSTR = [
    '/__pycache__/',
    '/.git/',
    '/.pytest_cache/',
    '/node_modules/',
    '/venv-core/',
    '/venv-image/',
    // Inactive image services (chatbot uses ComfyUI on :8188 directly — these
    // bundle their own ~90GB of model weights we don't need to ship).
    '/services/edit-image/',
    '/services/stable-diffusion/',
    '/services/stable-diffusion_upstream/',
    // Per-service caches / leftover envs / generated artifacts.
    '/services/chatbot/Storage/',
    '/services/chatbot/storage/',
    '/services/chatbot/local_data/',
    '/services/chatbot/private/',
    '/services/chatbot/models/',
    '/services/chatbot/venv/',
    '/services/chatbot/venv_chatbot_31233/',
    // ComfyUI runtime artifacts (kept dirs are recreated on first run).
    '/ComfyUI/output/',
    '/ComfyUI/temp/',
    '/ComfyUI/user/',
    '/ComfyUI/input/',
    '/ComfyUI/final/',
    '/app/logs/',
    '/app/local_data/',
    '/app/uploads/',
    '/app/storage/intermediate/',
    '/app/storage/outputs/',
    '/app/storage/character_research/',
    '/LORA/old/',
    '/LORA/new_1/',
    '/LORA/new_2/',
    '/LORA/eye_taped/',
    '/private/',
    '/app/character_select_stand_alone_app-main/',
    '/tests/',
    '/.vscode/',
    '/.github/',
];

const EXCLUDE_EXT = new Set([
    '.pyc', '.pyo', '.pyd-test', '.log',
    '.key', '.pem', '.p12', '.pfx', '.crt', '.cer',
]);
const EXCLUDE_NAMES = new Set([
    '.gitignore', '.gitattributes', '.gitkeep', '.dockerignore',
    'log_copilot.txt', '.DS_Store', 'Thumbs.db'
]);
const EXCLUDE_NAME_SUFFIX = ['.zip']; // LORA/*.zip etc.
// Substring patterns applied to lowercase basename.  Keep these narrow:
// cert/key extensions are already covered by EXCLUDE_EXT, so this list should
// only catch real credential filenames (e.g. service-account keys, RSA keys).
// Avoid generic words like "secret" or "token" — they match source files such
// as core/secret_key.py and tokenizer assets used by ComfyUI models.
const SECRET_NAME_PARTS = [
    'credential', 'credentials', 'id_rsa', 'private_key', 'service-account'
];

function isRealEnvFile(base) {
    const lower = base.toLowerCase();
    if (lower === '.env.example') return false;
    return lower === '.env' || lower.startsWith('.env_') || lower.startsWith('.env.');
}

function shouldSkip(srcPath) {
    const rel = '/' + path.relative(REPO_ROOT, srcPath).replace(/\\/g, '/') + '/';
    for (const sub of EXCLUDE_SUBSTR) if (rel.includes(sub)) return true;
    const base = path.basename(srcPath);
    const lowerBase = base.toLowerCase();
    if (isRealEnvFile(base)) return true;
    if (SECRET_NAME_PARTS.some((part) => lowerBase.includes(part))) return true;
    if (EXCLUDE_NAMES.has(base)) return true;
    if (EXCLUDE_EXT.has(path.extname(base).toLowerCase())) return true;
    for (const suf of EXCLUDE_NAME_SUFFIX) if (base.toLowerCase().endsWith(suf)) return true;
    return false;
}

async function copyItem(item) {
    const src = path.join(REPO_ROOT, item.src);
    const dst = path.join(PAYLOAD, item.dst);
    if (!await fs.pathExists(src)) {
        if (item.required) throw new Error('Missing required source: ' + src);
        console.log('[skip] not found: ' + item.src);
        return;
    }
    console.log('[copy] ' + item.src + ' -> payload/' + item.dst);
    await fs.copy(src, dst, {
        overwrite: true,
        errorOnExist: false,
        // Follow symlinks: copy them as regular files/dirs. Otherwise NSIS-side
        // mklink fails without admin and copy() throws EPERM. Filter still
        // applies on the source path so excluded subtrees stay excluded.
        dereference: true,
        preserveTimestamps: true,
        filter: (s) => !shouldSkip(s),
    });
}

function dirSizeSync(p) {
    let total = 0;
    const walk = (cur) => {
        let st;
        try { st = fs.lstatSync(cur); } catch { return; }
        if (st.isFile()) { total += st.size; return; }
        if (!st.isDirectory()) return;
        for (const name of fs.readdirSync(cur)) walk(path.join(cur, name));
    };
    walk(p);
    return total;
}

function humanSize(bytes) {
    const u = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0, n = bytes;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return n.toFixed(2) + ' ' + u[i];
}

async function main() {
    console.log('[prepare-payload] repo root: ' + REPO_ROOT);
    console.log('[prepare-payload] payload  : ' + PAYLOAD);

    if (await fs.pathExists(PAYLOAD)) {
        console.log('[prepare-payload] cleaning previous payload (preserving python311/ + wheels/)...');
        for (const name of await fs.readdir(PAYLOAD)) {
            if (name === 'python311' || name === 'wheels') continue;
            await fs.remove(path.join(PAYLOAD, name));
        }
    } else {
        await fs.mkdirp(PAYLOAD);
    }

    for (const item of COPY_ITEMS) {
        await copyItem(item);
    }

    // setup_venvs.py is shipped under payload/scripts so the NSIS hook can
    // run it via the bundled Python.
    const setupSrc = path.join(__dirname, 'setup_venvs.py');
    if (await fs.pathExists(setupSrc)) {
        await fs.mkdirp(path.join(PAYLOAD, 'scripts'));
        await fs.copy(setupSrc, path.join(PAYLOAD, 'scripts', 'setup_venvs.py'), { overwrite: true });
        console.log('[copy] scripts/setup_venvs.py -> payload/scripts/');
    } else {
        console.warn('[warn] scripts/setup_venvs.py not found — postinstall will fail!');
    }

    // Sanity warnings about pieces the user must provide.
    const py = path.join(PAYLOAD, 'python311', 'python.exe');
    if (!await fs.pathExists(py)) {
        console.warn('\n[warn] payload/python311/python.exe is missing.');
        console.warn('       Drop a portable Python 3.11 there before running electron-builder.');
        console.warn('       See app/electron/PACKAGING.md for instructions.\n');
    }
    for (const w of ['wheels/core', 'wheels/image']) {
        if (!await fs.pathExists(path.join(PAYLOAD, w))) {
            console.warn('[warn] payload/' + w + ' is missing — pip install will fail offline.');
        }
    }

    const sz = dirSizeSync(PAYLOAD);
    console.log('\n[prepare-payload] DONE. Payload size: ' + humanSize(sz));
}

if (require.main === module) {
    main().catch((err) => {
        console.error('[prepare-payload] FAILED: ' + (err && err.stack ? err.stack : err));
        process.exit(1);
    });
}

module.exports = { shouldSkip, isRealEnvFile };
