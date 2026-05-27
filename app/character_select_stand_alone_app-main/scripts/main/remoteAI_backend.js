import { ipcMain, net } from 'electron';

const CAT = '[ModelAPI]';

function requestRemote(options) {
    return new Promise((resolve, reject) => {
        const { apiUrl, apiKey, modelSelect, userPrompt, systemPrompt, timeout } = options;

        const requestBody = {
            model: modelSelect,
            messages: [
                { role: 'system', content: systemPrompt },
                { role: 'user', content: `${userPrompt};Response in English` }
            ],
        };
        const body = JSON.stringify(requestBody);

        let request = net.request({
            method: 'POST',
            url: apiUrl,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`,
            },
            timeout: timeout,
        });
       

        request.on('response', (response) => {
            let responseData = ''            
            response.on('data', (chunk) => {
                responseData += chunk
            })
            response.on('end', () => {
                if (response.statusCode !== 200) {
                    console.error(`${CAT} HTTP error: ${response.statusCode} - ${responseData}`);
                    resolve(`Error: HTTP error: ${response.statusCode}`);
                }

                resolve(responseData);
            })
        })

        request.on('error', (error) => {
            let ret = '';
            if (error.code === 'ECONNABORTED') {
                console.error(`${CAT} Request timed out after ${timeout}ms`);
                ret = `Request timed out after ${timeout}ms`;
            } else {
                console.error(CAT, 'Request failed:', error.message);
                ret = `Request failed:, ${error.message}`;
            }
            resolve(ret);
        });

        request.on('timeout', () => {
            req.destroy();
            console.error(`${CAT} Request timed out after ${timeout}ms`);
            resolve(`Error: Request timed out after ${timeout}ms`);
        });

        request.write(body);
        request.end();        
    });
}

function requestLocal(options) {
    return new Promise((resolve, reject) => {
        const { apiUrl, userPrompt, systemPrompt, temperature, n_predict, timeout } = options;

        const requestBody = {
            temperature: temperature,
            n_predict: n_predict,
            cache_prompt: true,
            stop: ["<|im_end|>"],
            messages: [
                { role: 'system', content: systemPrompt },
                { role: 'user', content: `${userPrompt};Response in English` }
            ],
        };
        const body = JSON.stringify(requestBody);

        let request = net.request({
            method: 'POST',
            url: apiUrl,
            headers: {
                'Content-Type': 'application/json'
            },
            timeout: timeout,
        });
       

        request.on('response', (response) => {
            let responseData = ''            
            response.on('data', (chunk) => {
                responseData += chunk
            })
            response.on('end', () => {
                if (response.statusCode !== 200) {
                    console.error(`${CAT} HTTP error: ${response.statusCode} - ${responseData}`);
                    resolve(`Error: HTTP error: ${response.statusCode}`);
                }

                resolve(responseData);
            })
        })

        request.on('error', (error) => {
            let ret = '';
            if (error.code === 'ECONNABORTED') {
                console.error(`${CAT} Request timed out after ${timeout}ms`);
                ret = `Request timed out after ${timeout}ms`;
            } else {
                console.error(CAT, 'Request failed:', error.message);
                ret = `Request failed:, ${error.message}`;
            }
            resolve(ret);
        });

        request.on('timeout', () => {
            req.destroy();
            console.error(`${CAT} Request timed out after ${timeout}ms`);
            resolve(`Error: Request timed out after ${timeout}ms`);
        });

        request.write(body);
        request.end();        
    });
}

function setupModelApi() {
    ipcMain.handle('request-ai-remote', async (event, options) => {
        return await requestRemote(options);
    });

    ipcMain.handle('request-ai-local', async (event, options) => {
        return await requestLocal(options);
    });
}

async function remoteAI(options){
    return await requestRemote(options);
}

async function localAI(options){
    return await requestLocal(options);
}

export {
    setupModelApi,
    remoteAI,
    localAI
};