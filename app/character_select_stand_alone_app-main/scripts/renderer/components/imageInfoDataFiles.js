// helper for pasted json/csv file items
export async function handlePastedJsonOrCsvFile(item, hideOverlay) {
    const file = item.getAsFile();
    if (!file) return false;
    console.log('Pasted file:', file.name);
    await globalThis.jsonlist.addJsonSlotFromFile(file, file.type);
    globalThis.collapsedTabs.jsonlist.setCollapsed(false);
    hideOverlay();
    return true;
}

// helper for pasted plain text items (keeps async logic inside callback but not nested deeply)
export function handlePastedPlainTextItem(item, hideOverlay) {
    return new Promise((resolve) => {
        item.getAsString(async (text) => {
            try {
                // Try parsing as JSON
                JSON.parse(text);
                const file = new File([text], 'pasted_data.json', { type: 'application/json', lastModified: Date.now() });
                console.log('Pasted JSON text:', file.name);
                await globalThis.jsonlist.addJsonSlotFromFile(file, 'application/json');
                globalThis.collapsedTabs.jsonlist.setCollapsed(false);
                hideOverlay();
                resolve(true);
            } catch (err) {
                console.error('Failed to parse pasted text as JSON:', err);
                // If not JSON, treat as CSV (basic validation: check for comma-separated values)
                if (text.includes(',')) {
                    const file = new File([text], 'pasted_data.csv', { type: 'text/csv', lastModified: Date.now() });
                    console.log('Pasted CSV text:', file.name);
                    await globalThis.jsonlist.addJsonSlotFromFile(file, 'text/csv');
                    globalThis.collapsedTabs.jsonlist.setCollapsed(false);
                    hideOverlay();
                    resolve(true);
                } else {
                    console.warn('Pasted text is not valid JSON or CSV:', text.slice(0, 50));
                    hideOverlay();
                    resolve(true);
                }
            }
        });
    });
}
