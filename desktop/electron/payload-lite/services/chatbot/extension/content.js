/**
 * AI Assistant Extension — Content Script
 * Captures page context and selected text
 */

// Listen for messages from popup or background
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'GET_SELECTION') {
        const selection = window.getSelection().toString();
        sendResponse({ selection });
    }

    if (message.type === 'GET_PAGE_CONTENT') {
        const content = {
            url: window.location.href,
            title: document.title,
            text: document.body.innerText.substring(0, 10000),
            selection: window.getSelection().toString(),
            meta: {
                description: document.querySelector('meta[name="description"]')?.content || '',
                keywords: document.querySelector('meta[name="keywords"]')?.content || ''
            }
        };
        sendResponse(content);
    }

    return true;
});

// Add keyboard shortcut listener (Ctrl+Shift+A to capture selection)
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'A') {
        const selection = window.getSelection().toString();
        if (selection) {
            chrome.runtime.sendMessage({
                type: 'QUICK_CAPTURE',
                data: {
                    selection,
                    url: window.location.href,
                    title: document.title
                }
            });
        }
    }
});
