/* prepare-payload-lite.js
 *
 * Stages the LITE payload into desktop/electron/payload-lite/.
 *
 * Goal: produce an installer of a few hundred MB (no models, no wheels,
 * no bundled Python). Everything heavy is downloaded / installed on the
 * target machine by the prereq bootstrapper + online pip install.
 *
 * Bundled:
 *   - All Python source (services/, app/config|src|scripts|requirements/, ComfyUI/,
 *     image_pipeline/, configs/, rag/)
 *   - storage/character_db, storage/metadata, storage/prompts (small JSON/YAML)
 *   - Root requirements*.txt
 *   - app/config/.env.example  (real .env files are provisioned on install)
 *   - bootstrap_prereqs.ps1 + setup_lite.py
 *
 * Excluded (vs prepare-payload.js):
 *   - LORA/                      (model weights)
 *   - ComfyUI/models/            (model weights)
 *   - ComfyUI/custom_nodes/<x>/models/
 *   - storage/character_loras|character_refs|feature_layers|references
 *   - python311/                 (auto-installed by bootstrap)
 *   - wheels/                    (online pip install)
 *   - Any file matching model extensions (.safetensors, .ckpt, .pt, .pth,
 *     .gguf, .onnx, .tflite, *.bin > 10MB)
 *   - Real .env files, keys/certs/credential-like files
 *
 * Run:
 *   node scripts/prepare-payload-lite.js
 */
const fs   = require('fs-extra');
const path = require('path');

const ELECTRON_DIR = path.resolve(__dirname, '..');
const REPO_ROOT    = path.resolve(ELECTRON_DIR, '..', '..');
const PAYLOAD      = path.join(ELECTRON_DIR, 'payload-lite');

const COPY_ITEMS = [
    { src: 'services',                       dst: 'services',                       required: true  },
    { src: 'app/config',                     dst: 'app/config',                     required: true  },
    { src: 'app/src',                        dst: 'app/src',                        required: true  },
    { src: 'app/scripts',                    dst: 'app/scripts',                    required: false },
    { src: 'app/requirements',               dst: 'app/requirements',               required: true  },
    { src: 'ComfyUI',                        dst: 'ComfyUI',                        required: true  },
    { src: 'image_pipeline',                 dst: 'image_pipeline',                 required: true  },
    { src: 'configs',                        dst: 'configs',                        required: true  },
    { src: 'rag',                            dst: 'rag',                            required: false },
    { src: 'storage/character_db',           dst: 'storage/character_db',           required: false },
    { src: 'storage/metadata',               dst: 'storage/metadata',               required: false },
    { src: 'storage/prompts',                dst: 'storage/prompts',                required: false },
    { src: 'storage/lora_inventory.json',    dst: 'storage/lora_inventory.json',    required: false },
    { src: 'requirements.txt',               dst: 'requirements.txt',               required: false },
    { src: 'requirements-core.txt',          dst: 'requirements-core.txt',          required: false },
    { src: 'requirements-image.txt',         dst: 'requirements-image.txt',         required: false },
];

// Substring exclusions on '/' + relative-path + '/'.
const EXCLUDE_SUBSTR = [
    '/__pycache__/',
    '/.git/',
    '/.pytest_cache/',
    '/node_modules/',
    '/venv-core/',
    '/venv-image/',
    // Inactive image services (chatbot uses ComfyUI on :8188 directly).
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
    // ComfyUI runtime artifacts + bundled model dirs.
    '/ComfyUI/output/',
    '/ComfyUI/temp/',
    '/ComfyUI/user/',
    '/ComfyUI/input/',
    '/ComfyUI/final/',
    '/ComfyUI/models/',
    // ComfyUI custom_node bundled models (each node may ship its own).
    '/custom_nodes/comfyui_controlnet_aux/ckpts/',
    '/app/logs/',
    '/app/local_data/',
    '/app/uploads/',
    '/app/ComfyUI/',
    '/storage/intermediate/',
    '/storage/outputs/',
    '/storage/character_research/',
    '/storage/character_loras/',
    '/storage/character_refs/',
    '/storage/feature_layers/',
    '/storage/references/',
    '/private/',
    '/character_select_stand_alone_app-main/',
    '/tests/',
    '/.vscode/',
    '/.github/',
];

// Always exclude these file extensions (model weights, archives, etc.).
const EXCLUDE_EXT = new Set([
    '.pyc', '.pyo', '.pyd-test', '.log',
    '.safetensors', '.ckpt', '.pt', '.pth', '.gguf', '.onnx', '.tflite',
    '.zip', '.7z', '.tar', '.gz', '.rar',
    '.key', '.pem', '.p12', '.pfx', '.crt', '.cer',
]);
const EXCLUDE_NAMES = new Set([
    '.gitignore', '.gitattributes', '.gitkeep', '.dockerignore',
    'log_copilot.txt', '.DS_Store', 'Thumbs.db'
]);
const SECRET_NAME_PARTS = [
    'credential', 'credentials', 'id_rsa', 'private_key', 'service-account'
];

// Extra guard: any *.bin file larger than this is treated as a weight blob.
const LARGE_BIN_THRESHOLD = 10 * 1024 * 1024; // 10 MB

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
    const ext = path.extname(base).toLowerCase();
    if (EXCLUDE_EXT.has(ext)) return true;
    if (ext === '.bin') {
        try {
            const st = fs.statSync(srcPath);
            if (st.isFile() && st.size > LARGE_BIN_THRESHOLD) return true;
        } catch { /* ignore */ }
    }
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
    console.log('[copy] ' + item.src + ' -> payload-lite/' + item.dst);
    await fs.copy(src, dst, {
        overwrite: true,
        errorOnExist: false,
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
    console.log('[prepare-payload-lite] repo root: ' + REPO_ROOT);
    console.log('[prepare-payload-lite] payload  : ' + PAYLOAD);

    if (await fs.pathExists(PAYLOAD)) {
        console.log('[prepare-payload-lite] cleaning previous payload-lite/ ...');
        await fs.remove(PAYLOAD);
    }
    await fs.mkdirp(PAYLOAD);

    for (const item of COPY_ITEMS) {
        await copyItem(item);
    }

    // Ship setup_lite.py + bootstrap_prereqs.ps1 inside payload/scripts.
    const scriptDst = path.join(PAYLOAD, 'scripts');
    await fs.mkdirp(scriptDst);
    for (const name of ['setup_lite.py', 'bootstrap_prereqs.ps1']) {
        const s = path.join(__dirname, name);
        if (await fs.pathExists(s)) {
            await fs.copy(s, path.join(scriptDst, name), { overwrite: true });
            console.log('[copy] scripts/' + name + ' -> payload-lite/scripts/');
        } else {
            console.warn('[warn] scripts/' + name + ' not found — postinstall may fail!');
        }
    }

    const sz = dirSizeSync(PAYLOAD);
    console.log('\n[prepare-payload-lite] payload size: ' + humanSize(sz));
    console.log('[prepare-payload-lite] done.');
}

if (require.main === module) {
    main().catch((e) => { console.error(e); process.exit(1); });
}

module.exports = { shouldSkip, isRealEnvFile };
