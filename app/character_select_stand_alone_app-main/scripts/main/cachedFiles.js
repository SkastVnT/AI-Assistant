import { app, ipcMain, dialog } from 'electron';
import * as fs from 'node:fs';
import path from 'node:path';
import { loadCSVFile, loadJSONFile } from './fileHandlers.js';

const CAT = '[FileCache]';

let cachedCharacterThumb = {}; 
let cachedLanguages = {};
let cachedCharacter = {};
let cachedOCCharacter = {};
let cachedViewTags = {};
let cachedTagAssist = {}
let cachedLoadingWait = {};
let cachedLoadingFailed = {};
let cachedPrivacyBall = {};

const appPath = app.isPackaged ? path.join(path.dirname(app.getPath('exe')), 'resources', 'app') : app.getAppPath();

function setupCachedFiles(){
    function loadFileEx(saveDir, fileName, dataPointer)
    {
        const filePath = path.join(appPath, saveDir, fileName);
        if (fs.existsSync(filePath)) {       
            
            const ext = path.extname(filePath).toLowerCase();
                        
            if (ext === '.csv') {
                const data = loadCSVFile(filePath);      
                Object.assign(dataPointer, data);            
            } else if (ext === '.json') {
                const data = loadJSONFile(filePath);      
                Object.assign(dataPointer, data); 
            } else {
                console.error(`${CAT}: ${fileName} load failed`);
                return false;
            }
            console.log(`${CAT}: ${fileName} loaded into memory`);
        } else {
            console.error(`${CAT}: ${fileName} load failed`);
            dialog.showErrorBox(CAT, `${fileName} load failed`);
            return false;
        }
        return true;
    }

    function loadImageEx(filePath, fileName, dataPointer) {
        const fileFullPath = path.join(appPath, filePath, fileName);
        if (fs.existsSync(fileFullPath)) {
            try {
                const fileBuffer = fs.readFileSync(fileFullPath);               
                const base64Data = fileBuffer.toString('base64');
                dataPointer.data = base64Data;

                console.log(`${CAT}: ${fileName} loaded into memory, size: ${fileBuffer.length} bytes`);
                return true;
            } catch (error) {
                console.error(`${CAT}: Error loading ${fileName}: ${error.message}`);
                return false;
            }
        } else {
            console.error(`${CAT}: ${fileName} load failed - file does not exist at ${fileFullPath}`);
            return false;
        }
    }

    const thumb = loadFileEx('data', 'wai_character_thumbs.json', cachedCharacterThumb);
    const language = loadFileEx('data', 'language.json', cachedLanguages);
    const characters = loadFileEx('data', 'wai_characters.csv', cachedCharacter);
    const character_tag_assist = loadFileEx('data', 'wai_tag_assist.json', cachedTagAssist);
    const oc_characters = loadFileEx('data', 'original_character.json', cachedOCCharacter);
    const view_tags = loadFileEx('data', 'view_tags.json', cachedViewTags);

    let filePath = path.join('data', 'imgs');
    const loadingWait = loadImageEx(filePath, 'loading_wait.png', cachedLoadingWait);
    const loadingFailed = loadImageEx(filePath, 'loading_failed.png', cachedLoadingFailed);
    const privacyBall = loadImageEx(filePath, 'privacy_ball.png', cachedPrivacyBall);
    
    ipcMain.handle('get-cached-files', async () => {
        return {
            characterThumb: cachedCharacterThumb,
            languages: cachedLanguages,
            characters: cachedCharacter,
            ocCharacters: cachedOCCharacter,
            viewTags: cachedViewTags,
            tagAssist: cachedTagAssist,
            loadingWait: cachedLoadingWait,
            loadingFailed: cachedLoadingFailed,
            privacyBall: cachedPrivacyBall
        };
    });

    return thumb && language && characters && oc_characters && view_tags && character_tag_assist && loadingWait && loadingFailed && privacyBall;
}

function getCachedFiles() {
    return {
        characterThumb: cachedCharacterThumb,
        languages: cachedLanguages,
        characters: cachedCharacter,
        ocCharacters: cachedOCCharacter,
        viewTags: cachedViewTags,
        tagAssist: cachedTagAssist,
        loadingWait: cachedLoadingWait,
        loadingFailed: cachedLoadingFailed,
        privacyBall: cachedPrivacyBall
    };
}   

function getCachedFilesWithoutThumb() {
    return {
        //characterThumb: cachedCharacterThumb,
        languages: cachedLanguages,
        characters: cachedCharacter,
        ocCharacters: cachedOCCharacter,
        viewTags: cachedViewTags,
        tagAssist: cachedTagAssist,
        loadingWait: cachedLoadingWait,
        loadingFailed: cachedLoadingFailed,
        privacyBall: cachedPrivacyBall
    };
}   

function getCharacterThumb(md5Chara) {
    if (cachedCharacterThumb[md5Chara] === undefined) {
        console.warn(CAT, `Character thumb for ${md5Chara} not found in cache.`);
        return null;
    }
    
    return cachedCharacterThumb[md5Chara];
}

export {
    setupCachedFiles,
    getCachedFiles,
    getCachedFilesWithoutThumb,
    getCharacterThumb
};