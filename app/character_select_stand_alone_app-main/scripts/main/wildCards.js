import * as fs from 'node:fs';
import path from 'node:path';
import { app, ipcMain } from 'electron';

const CAT = '[Wildcards]';
const appPath = app.isPackaged ? path.join(path.dirname(app.getPath('exe')), 'resources', 'app') : app.getAppPath();

const wildcardsDir = path.join(appPath, 'data', 'wildcards');
let wildcardsList = [];
let wildcardsCache = {};

function getWildcardsList() {
    return wildcardsList;
}

/**
 * search for wildcards files in the directory
 * and return a list of file names without the .txt extension.
 */
function updateWildcardsList() {
    wildcardsList = [];
    try {
        const files = fs.readdirSync(wildcardsDir);
        for( const file of files ) {
            if (
                file.endsWith('.txt') &&
                /^[a-zA-Z0-9_-]+\.txt$/.test(file)
            ) {
                wildcardsList.push(file.slice(0, -4));
                console.log(CAT, 'Found wildcards file:', file);
            }
        }
    } catch (err) {
        console.error(CAT, 'Failed to scan directory:', err);
    }
    return wildcardsList;
}

/**
 * Decode wildcards file content and return a line based on the seed.
 * @param {string} text -  wildcards file content
 * @param {number} seed - random seed
 * @returns {string} - returns the line corresponding to the seed
 */
function parseWildcards(text, seed) {
    if (typeof seed !== 'number') seed = 0;
    if (seed < 0) seed = -seed;
    const lines = text.split(/\r?\n/).filter(line => line.trim() !== '');
    if (lines.length === 0) return '';
    const index = seed % lines.length;
    return lines[index];
}

function setupWildcardsHandlers() {
    updateWildcardsList();

    // Handle request to get the list of wildcards files
    ipcMain.handle('load-wildcards', async (event, fileName, seed) => {
        return await loadWildcard(fileName, seed);
    });

    // update the wildcards list and clear the cache
    ipcMain.handle('update-wildcards', async () => {
        return updateWildcards();
    });
}

function updateWildcards() {
    wildcardsCache = {};
    return updateWildcardsList();
}

async function loadWildcard(fileName, seed) {
    // fileName must be a string and not contain any path traversal characters
    if (
        typeof fileName !== 'string' ||
        fileName.includes('/') ||
        fileName.includes('\\') ||
        fileName.includes('..') ||
        fileName.trim() === ''
    ) {
        console.error('[wildcards] Invalid file name:', fileName);
        return '';
    }

    // only allow alphanumeric characters, underscores, and hyphens
    const safeFileName = fileName.replaceAll(/[^a-zA-Z0-9_-]/g, '');

    // check if the file is in list
    if (!wildcardsList.includes(safeFileName)) {
        console.error('[wildcards] File not in wildcards list:', safeFileName);
        return '';
    }

    // hits in the cache
    if (wildcardsCache[safeFileName]) {
        return parseWildcards(wildcardsCache[safeFileName], seed);
    }

    // load the file from disk
    const absPath = path.resolve(wildcardsDir, `${safeFileName}.txt`);
    if (path.dirname(absPath) !== wildcardsDir) {
        console.error('[wildcards] Attempt to access outside current directory:', absPath);
        return '';
    }

    try {
        const text = await fs.promises.readFile(absPath, 'utf-8');
        wildcardsCache[safeFileName] = text;
        return parseWildcards(text, seed);
    } catch (err) {
        console.error('[wildcards] Failed to load:', absPath, err);
        return '';
    }
}

export {
    setupWildcardsHandlers,
    getWildcardsList,
    updateWildcards,
    loadWildcard
};