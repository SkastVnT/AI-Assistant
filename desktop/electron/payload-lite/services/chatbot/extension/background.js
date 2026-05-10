/**
 * AI Assistant Extension — Background Service Worker
 * Handles context menu actions and message relay
 */

// Create context menu on install
chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: 'send-to-ai',
        title: 'Ask AI Assistant about this',
        contexts: ['selection']
    });

    chrome.contextMenus.create({
        id: 'send-page-to-ai',
        title: 'Send page to AI Assistant',
        contexts: ['page']
    });

    // Set default server URL
    chrome.storage.sync.get(['serverUrl', 'apiKey'], (result) => {
        if (!result.serverUrl) {
            chrome.storage.sync.set({ serverUrl: 'http://localhost:5000' });
        }
        // API key must be configured by the user — no hardcoded default
    });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
    const { serverUrl, apiKey } = await chrome.storage.sync.get(['serverUrl', 'apiKey']);
    const baseUrl = serverUrl || 'http://localhost:5000';
    const key = apiKey || '';

    if (info.menuItemId === 'send-to-ai') {
        // Send selected text as context + open popup
        const selection = info.selectionText || '';
        try {
            await fetch(`${baseUrl}/api/v1/context`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': key
                },
                body: JSON.stringify({
                    url: tab.url,
                    title: tab.title,
                    selection: selection
                })
            });
            
            // Store for popup to use
            chrome.storage.local.set({
                lastContext: {
                    text: selection,
                    url: tab.url,
                    title: tab.title,
                    timestamp: Date.now()
                }
            });
        } catch (e) {
            console.error('[AI Ext] Failed to send context:', e);
        }
    }

    if (info.menuItemId === 'send-page-to-ai') {
        // Get full page content via content script
        try {
            const [result] = await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                func: () => {
                    return {
                        text: document.body.innerText.substring(0, 8000),
                        url: window.location.href,
                        title: document.title
                    };
                }
            });

            if (result && result.result) {
                await fetch(`${baseUrl}/api/v1/context`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': key
                    },
                    body: JSON.stringify({
                        url: result.result.url,
                        title: result.result.title,
                        content: result.result.text
                    })
                });

                chrome.storage.local.set({
                    lastContext: {
                        text: result.result.text.substring(0, 200) + '...',
                        url: result.result.url,
                        title: result.result.title,
                        timestamp: Date.now()
                    }
                });
            }
        } catch (e) {
            console.error('[AI Ext] Failed to get page content:', e);
        }
    }
});

// Handle messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'GET_PAGE_INFO') {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]) {
                chrome.scripting.executeScript({
                    target: { tabId: tabs[0].id },
                    func: () => ({
                        url: window.location.href,
                        title: document.title,
                        selection: window.getSelection().toString(),
                        textPreview: document.body.innerText.substring(0, 300)
                    })
                }).then(([result]) => {
                    sendResponse(result?.result || {});
                }).catch(() => sendResponse({}));
            } else {
                sendResponse({});
            }
        });
        return true; // Keep channel open for async response
    }
});
