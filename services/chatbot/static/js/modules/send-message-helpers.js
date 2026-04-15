/**
 * Send-message helpers — extracted from ChatBotApp.sendMessage()
 * Each function handles one stage of the send-message pipeline.
 * The orchestrator (sendMessage) calls them in sequence.
 */

import { ImageGenV2 } from './image-gen-v2.js';

// ─── Utility ──────────────────────────────────────────────────

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

/** HTML-attribute-safe escaping */
function htmlAttrEsc(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// ─── 1. collectFormState ──────────────────────────────────────

/**
 * Gathers input value, staged files, form controls, active tools.
 * Auto-converts very long input to a staged .txt file.
 * Returns null when there is nothing to send.
 */
export async function collectFormState(app) {
    const elements = app.uiUtils.elements;

    // Auto-convert very long input to a staged .txt file
    const LONG_TEXT_THRESHOLD = 3000;
    const rawInput = elements.messageInput ? elements.messageInput.value : '';
    if (rawInput.length > LONG_TEXT_THRESHOLD && app._stagedFiles !== undefined) {
        const blob = new Blob([rawInput], { type: 'text/plain' });
        const file = new File([blob], 'message.txt', { type: 'text/plain' });
        try {
            const fileData = await app.fileHandler.processFile(file);
            app._stagedFiles.push(fileData);
            if (elements.messageInput) elements.messageInput.value = '';
            app._renderStagingArea && app._renderStagingArea();
        } catch (err) {
            console.error('[App] Auto-convert to file error:', err);
        }
    }

    const flushedFiles = app._flushStagedFiles ? app._flushStagedFiles() : [];
    const formValues = app.uiUtils.getFormValues();
    const message = formValues.message.trim();
    const sessionFiles = app.fileHandler.getSessionFiles();

    if (!message && sessionFiles.length === 0) return null;

    const activeTools = window.getActiveTools
        ? window.getActiveTools()
        : Array.from(app.activeTools);

    return { elements, flushedFiles, formValues, message, sessionFiles, activeTools };
}

// ─── 2. routeByIntent ─────────────────────────────────────────

/**
 * Decides which flow to execute: image-gen, img2img, or normal chat.
 */
export function routeByIntent(message, activeTools) {
    const imageGenToolActive = activeTools.includes('image-generation');
    const isImageIntent = message && (imageGenToolActive || ImageGenV2.isImageRequest(message));
    const isImg2Img = activeTools.includes('img2img');
    return { isImageIntent, imageGenToolActive, isImg2Img };
}

// ─── 3. prepareOutgoingPayload ────────────────────────────────

/**
 * Builds the augmented message with file context, MCP context,
 * quoted context. Resolves deepThinking mode.
 */
export function prepareOutgoingPayload(app, { message, formValues, sessionFiles }) {
    let deepThinking = formValues.deepThinking;
    if (deepThinking === 'auto' && window.coordinatedReasoning) {
        deepThinking = window.coordinatedReasoning.autoDecideMode(message);
        console.log('[App] Auto mode decided:', deepThinking ? 'deep thinking' : 'instant');
    }

    const originalUserMessage = message;
    let augmented = message;

    // Quoted context (select-and-reply)
    augmented = injectQuotedContext(app, augmented);

    // File context + vision images
    const imageDataUrls = [];
    if (sessionFiles.length > 0) {
        const result = injectFileContext(app, augmented, sessionFiles);
        augmented = result.message;
        imageDataUrls.push(...result.imageDataUrls);
        deepThinking = true;
        console.log('[App] Auto-enabled Deep Thinking due to attached files, images:', imageDataUrls.length);
    }

    // MCP context
    const mcpResult = injectMcpContext(app, augmented);
    augmented = mcpResult.message;

    return {
        message: augmented,
        originalUserMessage,
        deepThinking,
        imageDataUrls,
        mcpIndicator: mcpResult.mcpIndicator,
    };
}

/** Inject quoted context from select-and-reply */
function injectQuotedContext(app, message) {
    const quotedCtx = app.messageRenderer.consumeQuotedContext();
    if (quotedCtx) {
        return `[Ngữ cảnh được chọn — ưu tiên trả lời dựa trên đoạn này]\n> ${quotedCtx}\n\n${message}`;
    }
    return message;
}

/** Separate images from text files, build text context */
export function injectFileContext(app, message, sessionFiles) {
    const imageDataUrls = [];
    const textFiles = [];
    for (const file of sessionFiles) {
        if (file.type && file.type.startsWith('image/') && file.content && file.content.startsWith('data:')) {
            imageDataUrls.push(file.content);
        } else {
            textFiles.push(file);
        }
    }
    const fileContext = app.buildFileContext(textFiles);
    if (fileContext || imageDataUrls.length > 0) {
        const textPart = fileContext ? `${fileContext}\n\n` : '';
        const imagePart = imageDataUrls.length > 0
            ? `📷 ${imageDataUrls.length} image(s) attached for analysis.\n\n`
            : '';
        message = `${textPart}${imagePart}${message || 'Hãy phân tích các file được đính kèm.'}`;
    }
    return { message, imageDataUrls };
}

/** Inject MCP context if enabled (single source: MCPController) */
export function injectMcpContext(app, message) {
    const fullMcpContext = (window.mcpController && window.mcpController.getFullContextString)
        ? window.mcpController.getFullContextString()
        : '';
    let mcpIndicator = '';
    if (fullMcpContext) {
        message = `[MCP Context được cung cấp - hãy sử dụng thông tin này để trả lời]\n\n${fullMcpContext}\n\n---\n\nUser question: ${message}`;
        mcpIndicator = ' 📎 MCP';
        console.log('[App] MCP context injected, length:', fullMcpContext.length);
    }
    return { message, mcpIndicator };
}

// ─── 4. runImageRequestFlow ───────────────────────────────────

/**
 * Full image-gen V2 flow: provider choice → generate → display result.
 * Returns after completion (caller should return too).
 */
export async function runImageRequestFlow(app, { message, formValues, elements, flushedFiles }) {
    console.log('[App] Image generation routing:', message ? 'intent detected' : 'tool active');
    const timestamp = app.uiUtils.formatTimestamp(new Date());
    app.messageRenderer.addMessage(
        elements.chatContainer, message, true,
        formValues.model, formValues.context, timestamp
    );
    app.uiUtils.clearInput();

    // ── Provider choice dialog (LOCAL / API / CANCEL) ──
    const providerChoice = await showProviderChoiceDialog(elements);

    if (providerChoice === 'cancel') {
        app.messageRenderer.addMessage(
            elements.chatContainer,
            '⏰ Đã hủy tạo ảnh — không có phản hồi hoặc người dùng chọn HỦY.',
            false, formValues.model, formValues.context,
            app.uiUtils.formatTimestamp(new Date())
        );
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
        await app.saveCurrentSession(true);
        return;
    }

    const imageGenOptions = providerChoice === 'local'
        ? { quality: 'free', provider: 'comfyui' }
        : { quality: 'auto' };
    console.log('[App] Provider choice:', providerChoice, imageGenOptions);

    // ── Streaming status UI ──
    const { statusContainer, addStep, updateStep, headerIcon } = createImageStreamStatus(elements);

    const conversationId = app.chatManager.getCurrentSession()?.id || '';
    app.currentAbortController = new AbortController();

    let providerStep = null;
    const result = await app.imageGenV2.generateFromChatStream(
        message, conversationId, app.currentAbortController.signal,
        {
            onStatus: (data) => {
                if (data.phase === 'enhance') {
                    data.enhanced_prompt ? addStep('✨', 'Prompt enhanced', 'done') : addStep('✨', data.step, 'active');
                } else if (data.phase === 'select') {
                    data.providers ? addStep('📡', `Providers: ${data.providers.join(', ')}`, 'done') : addStep('🔍', data.step, 'active');
                } else {
                    addStep('⚙️', data.step, 'active');
                }
            },
            onProviderTry: (data) => {
                providerStep = addStep('🔄', `Trying ${data.provider} (${data.attempt}/${data.total_providers})...`, 'active');
            },
            onProviderFail: (data) => {
                updateStep(providerStep, '❌', `${data.provider} failed: ${data.error}`, 'fail');
                providerStep = null;
            },
            onProviderSuccess: (data) => {
                updateStep(providerStep, '✅', `${data.provider} / ${data.model} — ${Math.round(data.latency_ms)}ms`, 'done');
                headerIcon.textContent = '✅';
                headerIcon.classList.remove('spinning');
            },
            onError: (data) => {
                addStep('❌', data.error, 'fail');
                headerIcon.textContent = '❌';
                headerIcon.classList.remove('spinning');
            },
        },
        imageGenOptions,
    );

    // ── Display result ──
    displayImageGenResult(app, { result, providerChoice, message, formValues, elements, conversationId });
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    await app.saveCurrentSession(true);
}

/** 30-second provider choice dialog (LOCAL / API / CANCEL) */
function showProviderChoiceDialog(elements) {
    return new Promise((resolve) => {
        const TIMEOUT_SECONDS = 30;
        const choiceContainer = document.createElement('div');
        choiceContainer.className = 'message assistant';
        choiceContainer.innerHTML = `
            <div class="message__avatar message__avatar--agent"><img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false"></div>
            <div class="message__body">
                <div class="message-content">
                    <div class="igv2-provider-choice">
                        <div class="igv2-choice-header">
                            <span class="igv2-choice-icon">⚡</span>
                            <span class="igv2-choice-title">Chọn phương thức tạo ảnh</span>
                            <span class="igv2-choice-timer">${TIMEOUT_SECONDS}s</span>
                        </div>
                        <div class="igv2-choice-buttons">
                            <button class="igv2-choice-btn igv2-choice-local" data-choice="local">
                                <span class="igv2-choice-btn-icon">🖥️</span>
                                <span class="igv2-choice-btn-label">LOCAL</span>
                                <span class="igv2-choice-btn-desc">ComfyUI · Miễn phí</span>
                            </button>
                            <button class="igv2-choice-btn igv2-choice-api" data-choice="api">
                                <span class="igv2-choice-btn-icon">☁️</span>
                                <span class="igv2-choice-btn-label">API</span>
                                <span class="igv2-choice-btn-desc">Cloud · Nhanh & chất lượng</span>
                            </button>
                            <button class="igv2-choice-btn igv2-choice-cancel" data-choice="cancel">
                                <span class="igv2-choice-btn-icon">❌</span>
                                <span class="igv2-choice-btn-label">HỦY</span>
                                <span class="igv2-choice-btn-desc">Không tạo ảnh</span>
                            </button>
                        </div>
                        <div class="igv2-choice-progress">
                            <div class="igv2-choice-progress-bar"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        elements.chatContainer.appendChild(choiceContainer);
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;

        const timerEl = choiceContainer.querySelector('.igv2-choice-timer');
        const progressBar = choiceContainer.querySelector('.igv2-choice-progress-bar');
        let remaining = TIMEOUT_SECONDS;
        let resolved = false;

        const finalize = (choice) => {
            if (resolved) return;
            resolved = true;
            clearInterval(countdownInterval);
            choiceContainer.querySelectorAll('.igv2-choice-btn').forEach(btn => {
                btn.disabled = true;
                if (btn.dataset.choice === choice) btn.classList.add('selected');
                else btn.classList.add('dimmed');
            });
            timerEl.textContent = choice === 'cancel' ? 'Đã hủy' : choice === 'local' ? 'LOCAL' : 'API';
            resolve(choice);
        };

        choiceContainer.querySelectorAll('.igv2-choice-btn').forEach(btn => {
            btn.addEventListener('click', () => finalize(btn.dataset.choice));
        });

        const countdownInterval = setInterval(() => {
            remaining--;
            if (timerEl) timerEl.textContent = `${remaining}s`;
            if (progressBar) progressBar.style.width = `${(remaining / TIMEOUT_SECONDS) * 100}%`;
            if (remaining <= 0) finalize('cancel');
        }, 1000);
        if (progressBar) progressBar.style.width = '100%';
    });
}

/** Create streaming status container for image gen progress */
function createImageStreamStatus(elements) {
    const statusContainer = document.createElement('div');
    statusContainer.className = 'message assistant';
    statusContainer.innerHTML = `
        <div class="message__avatar message__avatar--agent"><img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false"></div>
        <div class="message__body">
            <div class="message-content">
                <div class="igv2-stream-status">
                    <div class="igv2-stream-header">
                        <span class="igv2-stream-icon spinning">⚙️</span>
                        <span class="igv2-stream-title">Image Generation</span>
                    </div>
                    <div class="igv2-stream-steps"></div>
                </div>
            </div>
        </div>
    `;
    elements.chatContainer.appendChild(statusContainer);
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;

    const stepsContainer = statusContainer.querySelector('.igv2-stream-steps');
    const headerIcon = statusContainer.querySelector('.igv2-stream-icon');

    const addStep = (icon, text, className = '') => {
        const step = document.createElement('div');
        step.className = `igv2-stream-step ${className}`;
        step.innerHTML = `<span class="igv2-step-icon">${icon}</span><span class="igv2-step-text">${text}</span>`;
        stepsContainer.appendChild(step);
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
        return step;
    };

    const updateStep = (stepEl, icon, text, className = '') => {
        if (!stepEl) return;
        stepEl.className = `igv2-stream-step ${className}`;
        stepEl.innerHTML = `<span class="igv2-step-icon">${icon}</span><span class="igv2-step-text">${text}</span>`;
    };

    return { statusContainer, addStep, updateStep, headerIcon };
}

/** Display image gen result (success or error) + multi-thinking analysis */
function displayImageGenResult(app, { result, providerChoice, message, formValues, elements, conversationId }) {
    if (result.success) {
        let imgSrc = '';
        let imageId = '';
        if (result.images?.length > 0 && result.images[0].url) {
            imgSrc = result.images[0].url;
            imageId = result.images[0].image_id || '';
        } else if (result.images_url?.length > 0) {
            imgSrc = result.images_url[0];
        }

        const meta = `🎨 **${result.provider}** / ${result.model} | ${Math.round(result.latency_ms)}ms | $${result.cost_usd}`;
        const enhanced = result.prompt_used ? `\n📝 ${result.prompt_used.substring(0, 150)}` : '';
        const promptEsc = htmlAttrEsc(result.prompt_used || message);
        const imgSrcAttr = htmlAttrEsc(imgSrc);
        const imageIdAttr = htmlAttrEsc(imageId);
        const overlayButtons = `
            <div class="igv2-img-overlay">
                <button type="button" class="igv2-img-btn" title="Tải ảnh" data-igv2-action="download" data-img-src="${imgSrcAttr}" data-image-id="${imageIdAttr}">⬇</button>
                <button type="button" class="igv2-img-btn" title="Thông tin" data-igv2-action="info" data-image-id="${imageIdAttr}">ℹ</button>
                ${imageId ? `<button type="button" class="igv2-img-btn igv2-save-btn" title="Lưu & Upload Drive" data-igv2-action="save" data-image-id="${imageIdAttr}">☁</button>` : ''}
            </div>`;
        app.messageRenderer.addMessage(
            elements.chatContainer,
            `<div class="igv2-chat-image" data-image-id="${imageIdAttr}" data-prompt="${promptEsc}">${overlayButtons}<img src="${imgSrc}" alt="Generated" data-igv2-open="${imgSrcAttr}"><div class="igv2-chat-meta">${meta}${enhanced}</div></div>`,
            false, formValues.model, formValues.context,
            app.uiUtils.formatTimestamp(new Date())
        );

        // Store image gen metadata for regeneration
        const lastAssistantMsg = elements.chatContainer.querySelector('.message.assistant:last-child');
        if (lastAssistantMsg) {
            lastAssistantMsg.dataset.igv2Provider = providerChoice;
            lastAssistantMsg.dataset.igv2Prompt = message;
            lastAssistantMsg.dataset.igv2RegenCount = '0';
            lastAssistantMsg.dataset.igv2ConversationId = conversationId;
            lastAssistantMsg.dataset.igv2IsImage = 'true';
        }

        // Multi-thinking analysis when multi-thinking mode
        if (formValues.thinkingMode === 'multi-thinking') {
            renderImageThinkingAnalysis(app, { result, providerChoice, message, formValues, elements });
        }
    } else {
        app.messageRenderer.addMessage(
            elements.chatContainer,
            `❌ Không thể tạo ảnh: ${result.error}`,
            false, formValues.model, formValues.context,
            app.uiUtils.formatTimestamp(new Date())
        );
        const lastErrMsg = elements.chatContainer.querySelector('.message.assistant:last-child');
        if (lastErrMsg) {
            lastErrMsg.dataset.igv2Provider = providerChoice;
            lastErrMsg.dataset.igv2Prompt = message;
            lastErrMsg.dataset.igv2RegenCount = '0';
            lastErrMsg.dataset.igv2ConversationId = conversationId;
            lastErrMsg.dataset.igv2IsImage = 'true';
        }
    }
}

/** 4-agents deep thinking analysis for image gen (multi-thinking mode) */
async function renderImageThinkingAnalysis(app, { result, providerChoice, message, formValues, elements }) {
    const thinkingSection = app.messageRenderer.createThinkingSection(null, true);
    const thinkMsgEl = document.createElement('div');
    thinkMsgEl.className = 'message assistant';
    thinkMsgEl.innerHTML = '<div class="message__avatar message__avatar--agent"><img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false"></div><div class="message__body"><div class="message-content"></div></div>';
    thinkMsgEl.querySelector('.message-content').appendChild(thinkingSection);
    elements.chatContainer.appendChild(thinkMsgEl);
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;

    const analysisSteps = [
        { icon: '🔍', text: `**Phân tích prompt** — "${(result.prompt_used || message).substring(0, 80)}..."` },
        { icon: '🎨', text: `**Provider:** ${result.provider} / ${result.model}` },
        { icon: '⚡', text: `**Hiệu suất:** ${Math.round(result.latency_ms)}ms · Chi phí: $${result.cost_usd}` },
        { icon: '📐', text: `**Đánh giá bố cục:** Ảnh được tạo với kích thước ${result.metadata?.width || '?'}×${result.metadata?.height || '?'}` },
        { icon: '✨', text: `**Chất lượng:** ${providerChoice === 'local' ? 'ComfyUI local — miễn phí, tùy chỉnh tốt' : 'Cloud API — chất lượng cao, tốc độ nhanh'}` },
        { icon: '✅', text: '**Kết luận:** Ảnh đã được tạo thành công. Bạn có thể yêu cầu chỉnh sửa thêm.' },
    ];

    for (let i = 0; i < analysisSteps.length; i++) {
        await new Promise(r => setTimeout(r, 400));
        app.messageRenderer.addThinkingStep(thinkingSection, `${analysisSteps[i].icon} ${analysisSteps[i].text}`);
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    }

    if (app.messageRenderer.finalizeThinking) {
        app.messageRenderer.finalizeThinking(thinkingSection);
    }
}

// ─── 5. runImg2ImgFlow ────────────────────────────────────────

/**
 * Img2Img flow: convert last image in conversation with a prompt.
 * Returns true if handled, false if no source image (fall through to chat).
 */
export async function runImg2ImgFlow(app, { message, formValues, elements }) {
    const allImages = elements.chatContainer.querySelectorAll(
        '.igv2-chat-image img, .generated-preview img, .message img[src*="/api/image-gen/"], .message img[src*="/storage/images/"]'
    );
    const lastImg = allImages.length > 0 ? allImages[allImages.length - 1] : null;

    if (!lastImg) {
        console.log('[App] Img2Img active but no source image found, falling through to chat');
        return false;
    }

    console.log('[App] Img2Img tool active, using last image as source');
    const timestamp = app.uiUtils.formatTimestamp(new Date());
    app.messageRenderer.addMessage(
        elements.chatContainer, message, true,
        formValues.model, formValues.context, timestamp
    );
    app.uiUtils.clearInput();

    app.messageRenderer.addMessage(
        elements.chatContainer,
        '🖼️ Đang chuyển đổi ảnh (Img2Img)...',
        false, formValues.model, formValues.context,
        app.uiUtils.formatTimestamp(new Date())
    );

    try {
        // Fetch source image as base64
        const imgResp = await fetch(lastImg.src);
        const blob = await imgResp.blob();
        const base64 = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });

        const result = await app.apiService.generateImg2Img({
            init_images: [base64],
            prompt: message,
            negative_prompt: 'bad quality, blurry, nsfw, nude',
            denoising_strength: 0.6,
            steps: 28,
            width: 512,
            height: 512,
        });

        // Remove loading message
        const lastAssistant = elements.chatContainer.querySelector('.message.assistant:last-child');
        if (lastAssistant) lastAssistant.remove();

        if (result.images && result.images.length > 0) {
            const imgSrc = result.images[0].startsWith('data:')
                ? result.images[0]
                : `data:image/png;base64,${result.images[0]}`;
            app.messageRenderer.addMessage(
                elements.chatContainer,
                `<div class="igv2-chat-image"><img src="${imgSrc}" alt="Img2Img Result"><div class="igv2-chat-meta">🖼️ Img2Img | Prompt: ${message.substring(0, 80)}</div></div>`,
                false, formValues.model, formValues.context,
                app.uiUtils.formatTimestamp(new Date())
            );
        } else {
            app.messageRenderer.addMessage(
                elements.chatContainer,
                `❌ Img2Img thất bại: ${result.error || 'Không nhận được ảnh'}`,
                false, formValues.model, formValues.context,
                app.uiUtils.formatTimestamp(new Date())
            );
        }
    } catch (e) {
        const lastAssistant = elements.chatContainer.querySelector('.message.assistant:last-child');
        if (lastAssistant) lastAssistant.remove();
        app.messageRenderer.addMessage(
            elements.chatContainer,
            `❌ Img2Img lỗi: ${e.message}`,
            false, formValues.model, formValues.context,
            app.uiUtils.formatTimestamp(new Date())
        );
    }

    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    await app.saveCurrentSession(true);
    return true;
}

// ─── 6. runStreamingChatFlow ──────────────────────────────────

/**
 * SSE streaming chat + fallback POST + finalize render + suggestions.
 * Handles its own try/catch/finally for clean orchestrator.
 */
export async function runStreamingChatFlow(app, ctx) {
    const {
        message, originalUserMessage, deepThinking,
        imageDataUrls, formValues, elements, activeTools, flushedFiles,
    } = ctx;

    // Generate message ID for versioning
    app.currentMessageId = 'msg_' + Date.now();

    const thinkingMode = formValues.thinkingMode || 'instant';
    app.uiUtils.showLoading(thinkingMode);
    if (window.showToolStatus) window.showToolStatus();

    // Show user message
    const timestamp = app.uiUtils.formatTimestamp(new Date());
    const customPromptUsed = window.customPromptEnabled === true;
    app.messageRenderer.addMessage(
        elements.chatContainer,
        originalUserMessage || message,
        true, formValues.model, formValues.context, timestamp,
        null, customPromptUsed, null,
        flushedFiles.length > 0 ? flushedFiles : null
    );

    // Image-generation loading placeholder
    let imageLoadingPlaceholder = null;
    const hasImageTool = activeTools.includes('image-generation');
    if (hasImageTool) {
        imageLoadingPlaceholder = createImageLoadingPlaceholder(elements);
    }

    // Close any open thinking panel
    if (window.ThinkingPanel) window.ThinkingPanel.close();
    let thinkingContainer = null;

    app.uiUtils.clearInput();
    app.currentAbortController = new AbortController();

    try {
        const history = app.buildConversationHistory();
        const selectedMemories = app.memoryManager.getSelectedMemories();
        const agentConfig = window.getAgentConfig ? window.getAgentConfig() : null;

        // ── SSE streaming ──
        let fullResponse = '';
        let thinkingSteps = [];
        let thinkingData = {};
        let streamFailed = false;
        let thinkingReceived = false;
        let streamCompleteData = {};
        let streamSuggestions = [];
        const _streamStartMs = performance.now();

        // Prepare streaming message div (hidden until first chunk)
        const responseTimestamp = app.uiUtils.formatTimestamp(new Date());
        const { streamMsgDiv, streamContentDiv, streamTextDiv } = createStreamingDiv(formValues, responseTimestamp);
        elements.chatContainer.appendChild(streamMsgDiv);

        // Shared mutable state bag — callbacks write, caller reads after stream ends
        const ss = {
            thinkingContainer, thinkingReceived, thinkingSteps, thinkingData,
            fullResponse, streamCompleteData, streamSuggestions, streamFailed,
            streamMsgDiv, streamTextDiv, elements,
        };

        try {
            await app.apiService.sendStreamMessage(
                {
                    message,
                    model: formValues.model,
                    context: formValues.context,
                    deepThinking,
                    thinkingMode,
                    history,
                    memories: selectedMemories,
                    customPrompt: agentConfig ? agentConfig.systemPrompt : '',
                    images: imageDataUrls.length > 0 ? imageDataUrls : undefined,
                    tools: activeTools,
                    skill: window.skillManager ? window.skillManager.getActiveSkillId() : '',
                    ...window.getAdvancedModelParams(),
                },
                app.currentAbortController.signal,
                buildStreamCallbacks(app, ss),
            );

            // Sync mutable state back
            ({ thinkingContainer, thinkingReceived, fullResponse, thinkingSteps, thinkingData,
               streamCompleteData, streamSuggestions, streamFailed } = ss);
        } catch (streamErr) {
            // Sync callback-mutated state even on error
            thinkingContainer = ss.thinkingContainer;
            if (streamErr.name === 'AbortError') throw streamErr;
            console.warn('[Stream] SSE failed, falling back to regular POST:', streamErr.message);
            streamFailed = true;
        }

        // ── Fallback to regular POST ──
        if (streamFailed) {
            streamMsgDiv.remove();
            const data = await app.apiService.sendMessage(
                message, formValues.model, formValues.context,
                activeTools, deepThinking, history, [],
                selectedMemories, app.currentAbortController.signal,
                agentConfig ? agentConfig.systemPrompt : '', agentConfig
            );
            fullResponse = data.error ? `❌ **Lỗi:** ${data.error}` : data.response;

            if (data.thinking_process) {
                if (!thinkingContainer) {
                    thinkingContainer = app.messageRenderer.createThinkingSection(null, false);
                    elements.chatContainer.insertBefore(thinkingContainer, streamMsgDiv.nextSibling || null);
                }
                app.messageRenderer.updateThinkingContent(thinkingContainer, data.thinking_process);
            } else if (thinkingContainer) {
                app.messageRenderer.finalizeThinking(thinkingContainer, { summary: 'Hoàn thành' });
            }
        }

        // ── Finalize display ──
        finalizeAssistantRender(app, {
            fullResponse, streamFailed, streamMsgDiv, streamContentDiv, streamTextDiv,
            imageLoadingPlaceholder, thinkingContainer, thinkingData, thinkingReceived,
            formValues, elements, _streamStartMs, streamCompleteData, customPromptUsed,
            responseTimestamp,
        });

        // ── Version history + session save ──
        persistResponse(app, {
            fullResponse, formValues, elements,
            message, streamFailed,
        });

        // ── Follow-up suggestions ──
        renderSuggestions(app, {
            streamFailed, streamSuggestions, fullResponse,
            message, formValues, elements, thinkingMode,
        });

    } catch (error) {
        handleSendFailure(app, {
            error, elements, formValues, thinkingContainer, imageLoadingPlaceholder,
        });
    } finally {
        if (window.hideToolStatus) window.hideToolStatus();
        app.uiUtils.hideLoading();
        app.currentAbortController = null;
    }
}

/** Create the hidden streaming message div */
function createStreamingDiv(formValues, responseTimestamp) {
    const streamMsgDiv = document.createElement('div');
    streamMsgDiv.className = 'message assistant';
    streamMsgDiv.dataset.timestamp = responseTimestamp;
    streamMsgDiv.dataset.model = formValues.model || '';
    streamMsgDiv.style.display = 'none';

    const streamAvatar = document.createElement('div');
    streamAvatar.className = 'message__avatar message__avatar--agent';
    streamAvatar.innerHTML = '<img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false">';
    streamMsgDiv.appendChild(streamAvatar);

    const streamBody = document.createElement('div');
    streamBody.className = 'message__body';
    const streamContentDiv = document.createElement('div');
    streamContentDiv.className = 'message-content';
    const streamTextDiv = document.createElement('div');
    streamTextDiv.className = 'message-text streaming-cursor';
    streamContentDiv.appendChild(streamTextDiv);
    streamBody.appendChild(streamContentDiv);
    streamMsgDiv.appendChild(streamBody);

    return { streamMsgDiv, streamContentDiv, streamTextDiv };
}

/** Create image-generation loading placeholder */
function createImageLoadingPlaceholder(elements) {
    const placeholder = document.createElement('div');
    placeholder.className = 'message assistant';
    placeholder.innerHTML = `
        <div class="message__avatar message__avatar--agent"><img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false"></div>
        <div class="message__body">
            <div class="message-content">
                <div class="image-gen-loading" id="imageGenLoadingPlaceholder">
                    <div class="loading-spinner"></div>
                    <div class="loading-text">🎨 Đang tạo ảnh...</div>
                    <div class="loading-progress" style="font-size:11px;color:var(--text-tertiary);">Analyzing prompt → Selecting provider → Generating</div>
                </div>
            </div>
        </div>
    `;
    elements.chatContainer.appendChild(placeholder);
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    return placeholder;
}

// ─── SSE Callbacks ────────────────────────────────────────────

/**
 * Build SSE stream callbacks. All callbacks mutate the shared state
 * object `s` so the outer scope can read updated values after streaming.
 */
export function buildStreamCallbacks(app, s) {
    return {
        onMetadata: (data) => {
            if (window.skillManager && data.skill_source === 'auto' && data.skill) {
                window.skillManager.showAutoRouted(data.skill, data.skill_name, data.skill_auto_keywords);
            }
        },
        onThinkingStart: (data) => {
            s.thinkingReceived = true;
            if (!s.thinkingContainer) {
                s.thinkingContainer = app.messageRenderer.createThinkingSection(null, true);
                s.streamMsgDiv.parentNode.insertBefore(s.thinkingContainer, s.streamMsgDiv);
            }
            if (data?.request_id && s.thinkingContainer) {
                s.thinkingContainer.dataset.requestId = data.request_id;
            }
        },
        onThinking: (data) => {
            s.thinkingReceived = true;
            if (!s.thinkingContainer) {
                s.thinkingContainer = app.messageRenderer.createThinkingSection(null, true);
                s.streamMsgDiv.parentNode.insertBefore(s.thinkingContainer, s.streamMsgDiv);
            }
            if (data?.request_id && s.thinkingContainer) {
                s.thinkingContainer.dataset.requestId = data.request_id;
            }
            s.thinkingSteps.push(data.step);
            app.messageRenderer.addThinkingStep(
                s.thinkingContainer, data.step, !!data.is_reasoning_chunk,
                data.trajectory_id || null
            );
            s.elements.chatContainer.scrollTop = s.elements.chatContainer.scrollHeight;
        },
        onThinkingEnd: (data) => {
            s.thinkingData = data;
            if (s.thinkingContainer) {
                if (data?.request_id) s.thinkingContainer.dataset.requestId = data.request_id;
                app.messageRenderer.finalizeThinking(s.thinkingContainer, data);
            }
        },
        onChunk: (data) => {
            if (s.thinkingContainer && !s.thinkingReceived) {
                s.thinkingContainer.remove();
                s.thinkingContainer = null;
            }
            if (s.streamMsgDiv.style.display === 'none') {
                s.streamMsgDiv.style.display = '';
            }
            s.fullResponse += data.content;
            if (typeof marked !== 'undefined') {
                const rawHtml = marked.parse(s.fullResponse);
                s.streamTextDiv.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(rawHtml) : rawHtml;
            } else {
                s.streamTextDiv.textContent = s.fullResponse;
            }
            s.elements.chatContainer.scrollTop = s.elements.chatContainer.scrollHeight;
        },
        onComplete: (data) => {
            s.fullResponse = data.response || s.fullResponse;
            s.streamCompleteData = data;
            if (s.thinkingContainer && !s.thinkingReceived) {
                s.thinkingContainer.remove();
                s.thinkingContainer = null;
            }
            if (s.thinkingContainer && app.messageRenderer.finalizeThinking) {
                app.messageRenderer.finalizeThinking(s.thinkingContainer, {});
            }
        },
        onSuggestions: (data) => {
            if (data.items && data.items.length > 0) {
                s.streamSuggestions = data.items;
            }
        },
        onError: (data) => {
            console.error('[Stream] Error:', data.error);
            s.streamFailed = true;
        },
    };
}

// ─── 7. finalizeAssistantRender ───────────────────────────────

/**
 * Finalize the assistant response display: handle image responses,
 * stream finalization, code highlighting, stats badge, buttons.
 */
export function finalizeAssistantRender(app, ctx) {
    const {
        fullResponse, streamFailed, streamMsgDiv, streamContentDiv, streamTextDiv,
        imageLoadingPlaceholder, thinkingContainer, thinkingData, thinkingReceived,
        formValues, elements, _streamStartMs, streamCompleteData, customPromptUsed,
        responseTimestamp,
    } = ctx;

    const responseContent = fullResponse;

    // Handle image response from tool
    const isImageResponse = responseContent && (
        responseContent.includes('Image Generated') ||
        responseContent.includes('generated-preview') ||
        responseContent.includes('Image Generation Failed')
    );

    if (imageLoadingPlaceholder && isImageResponse) {
        const resultDiv = buildImageResultDiv(app, responseContent, formValues, responseTimestamp);
        imageLoadingPlaceholder.replaceWith(resultDiv);
        if (window.lucide) lucide.createIcons({ nodes: [resultDiv] });
        streamMsgDiv.remove();
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
        return;
    }

    // Non-image path
    if (imageLoadingPlaceholder) imageLoadingPlaceholder.remove();
    streamTextDiv.classList.remove('streaming-cursor');

    if (!streamFailed && streamMsgDiv.style.display !== 'none') {
        // Finalize streamed message
        if (typeof marked !== 'undefined') {
            const rawHtml = marked.parse(responseContent);
            streamTextDiv.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(rawHtml) : rawHtml;
        }
        if (typeof hljs !== 'undefined') {
            streamTextDiv.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
        }
        app.messageRenderer.enhanceCodeBlocks(streamTextDiv);
        app.messageRenderer.enhanceMarkdownTables(streamTextDiv);
        app.messageRenderer.addMessageButtons(streamContentDiv, responseContent, false, streamMsgDiv);

        // Stats badge
        const thinkingMode = formValues.thinkingMode || 'instant';
        const _clientElapsed = (performance.now() - _streamStartMs) / 1000;
        const _serverElapsed = streamCompleteData.elapsed_time || _clientElapsed;
        const _tokens = streamCompleteData.tokens || 0;
        const _maxTokens = streamCompleteData.max_tokens || 0;
        const _modelName = app.messageRenderer.modelNames[formValues.model] || formValues.model;
        const _speedLabel = _serverElapsed < 2 ? 'Fast' : _serverElapsed < 5 ? '' : 'Slow';
        app.messageRenderer.addResponseStats(streamContentDiv, {
            elapsed: _serverElapsed,
            model: _modelName,
            tokens: _tokens,
            maxTokens: _maxTokens,
            speedLabel: _speedLabel,
            thinkingMode,
        });

        if (window.lucide) lucide.createIcons({ nodes: [streamMsgDiv] });
    } else if (streamFailed) {
        const agentConfigForDisplay = window.getAgentConfig ? window.getAgentConfig() : null;
        app.messageRenderer.addMessage(
            elements.chatContainer, responseContent,
            false, formValues.model, formValues.context, responseTimestamp,
            thinkingData.steps || null, customPromptUsed, agentConfigForDisplay
        );
    }
}

/** Build a result div for image-tool responses */
function buildImageResultDiv(app, responseContent, formValues, responseTimestamp) {
    const resultDiv = document.createElement('div');
    resultDiv.className = 'message assistant';
    resultDiv.dataset.timestamp = responseTimestamp;
    resultDiv.dataset.model = formValues.model || '';

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message__avatar message__avatar--agent';
    avatarDiv.innerHTML = '<img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false">';
    resultDiv.appendChild(avatarDiv);

    const bodyDiv = document.createElement('div');
    bodyDiv.className = 'message__body';
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    const textDiv = document.createElement('div');
    textDiv.className = 'message-text image-gen-result';

    if (typeof marked !== 'undefined') {
        const rawHtml = marked.parse(responseContent);
        textDiv.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(rawHtml) : rawHtml;
    } else {
        textDiv.textContent = responseContent;
    }
    contentDiv.appendChild(textDiv);
    bodyDiv.appendChild(contentDiv);
    app.messageRenderer.addMessageButtons(contentDiv, responseContent, false, resultDiv);
    resultDiv.appendChild(bodyDiv);
    return resultDiv;
}

// ─── 8. persistResponse ───────────────────────────────────────

/** Save response to version history, session, Firebase. Make images clickable. */
function persistResponse(app, { fullResponse, formValues, elements, message, streamFailed }) {
    const responseTimestamp = app.uiUtils.formatTimestamp(new Date());

    // Update latest version with assistant response
    const userMessages = elements.chatContainer.querySelectorAll('.message.user[data-message-id]');
    if (userMessages.length > 0) {
        const lastUserMsg = userMessages[userMessages.length - 1];
        const messageId = lastUserMsg.dataset.messageId;
        if (messageId) {
            const msgHistory = app.messageRenderer.getMessageHistory(messageId);
            if (msgHistory.length > 0) {
                msgHistory[msgHistory.length - 1].assistantResponse = fullResponse;
                if (window.chatManager) {
                    const session = window.chatManager.getCurrentSession();
                    if (session?.messageVersions?.[messageId]) {
                        const versions = session.messageVersions[messageId];
                        if (versions.length > 0) {
                            versions[versions.length - 1].assistantResponse = fullResponse;
                            window.chatManager.saveSessions();
                        }
                    }
                }
            }
        }
    }

    // Save to version history
    if (!app.messageHistory[app.currentMessageId]) {
        app.messageHistory[app.currentMessageId] = [];
    }
    app.messageHistory[app.currentMessageId].push({
        version: 1,
        content: fullResponse,
        timestamp: responseTimestamp,
        model: formValues.model,
        context: formValues.context,
    });

    app.saveCurrentSession(true);
    app.autoGenerateTitleIfNeeded(formValues.message.trim());

    // Firebase logging (async, non-blocking)
    if (window.logChatToFirebase && !streamFailed) {
        window.logChatToFirebase(message, formValues.model, fullResponse, []);
    }

    // Make images clickable
    const makeClickable = () => app.messageRenderer.makeImagesClickable((img) => app.openImagePreview(img));
    setTimeout(makeClickable, 100);
    setTimeout(makeClickable, 500);
}

// ─── 9. renderSuggestions ─────────────────────────────────────

/** Follow-up suggestion chips + "Think Harder" button */
function renderSuggestions(app, { streamFailed, streamSuggestions, fullResponse, message, formValues, elements, thinkingMode }) {
    if (streamFailed || app.messageRenderer.features?.suggestionChips === false) return;

    const suggestionsContainer = document.createElement('div');
    suggestionsContainer.className = 'follow-up-suggestions';

    // "Think Harder" button (only in instant mode)
    if (thinkingMode === 'instant') {
        const thinkBtn = document.createElement('button');
        thinkBtn.className = 'suggestion-chip suggestion-chip--think';
        thinkBtn.innerHTML = '<i data-lucide="brain" class="lucide"></i> Deep Thinking';
        thinkBtn.title = '4-Agents involvement';
        thinkBtn.onclick = () => {
            suggestionsContainer.remove();
            if (window.selectThinkingMode) {
                window.selectThinkingMode('multi-thinking', 'layers', '4-Agents');
            }
            app.uiUtils.setInputValue(message);
            setTimeout(() => { document.getElementById('sendBtn')?.click(); }, 100);
        };
        suggestionsContainer.appendChild(thinkBtn);
    }

    elements.chatContainer.appendChild(suggestionsContainer);
    if (window.lucide) lucide.createIcons({ nodes: [suggestionsContainer] });

    const _renderChips = (suggestions) => {
        suggestionsContainer.querySelectorAll('.suggestion-chip--loading').forEach(el => el.remove());
        suggestions.forEach(text => {
            const chip = document.createElement('button');
            chip.className = 'suggestion-chip';
            chip.innerHTML = `<span class="suggestion-chip__icon">↗</span><span class="suggestion-chip__text">${escapeHtml(text)}</span>`;
            chip.onclick = () => {
                suggestionsContainer.remove();
                app.uiUtils.setInputValue(text);
                setTimeout(() => { document.getElementById('sendBtn')?.click(); }, 100);
            };
            suggestionsContainer.appendChild(chip);
        });
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    };

    if (streamSuggestions.length > 0) {
        _renderChips(streamSuggestions);
    } else if (fullResponse) {
        // Skeleton placeholders while fetching
        for (let i = 0; i < 3; i++) {
            const s = document.createElement('span');
            s.className = 'suggestion-chip suggestion-chip--loading';
            s.innerHTML = '<span class="suggestion-chip__icon">↗</span><span class="suggestion-chip__text">…</span>';
            suggestionsContainer.appendChild(s);
        }
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;

        const _lang = /[àáâãäåæçèéêëìíîïðñòóôõöøùúûüý]/i.test(fullResponse) ? 'vi' : 'en';
        fetch('/api/chat/suggestions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message.slice(0, 500),
                response: fullResponse.slice(0, 1000),
                model: formValues.model,
                language: _lang,
            }),
            signal: AbortSignal.timeout(15000),
        })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (data?.suggestions?.length > 0) {
                _renderChips(data.suggestions);
            } else {
                suggestionsContainer.querySelectorAll('.suggestion-chip--loading').forEach(el => el.remove());
            }
        })
        .catch(() => {
            suggestionsContainer.querySelectorAll('.suggestion-chip--loading').forEach(el => el.remove());
        });
    }
}

// ─── 10. handleSendFailure ────────────────────────────────────

/** Handle errors in the chat send flow */
export function handleSendFailure(app, { error, elements, formValues, thinkingContainer, imageLoadingPlaceholder }) {
    if (thinkingContainer) thinkingContainer.remove();
    if (imageLoadingPlaceholder) imageLoadingPlaceholder.remove();

    if (error.name === 'AbortError') {
        console.log('Generation stopped by user');
        return;
    }

    const errorTimestamp = app.uiUtils.formatTimestamp(new Date());
    const customPromptUsed = window.customPromptEnabled === true;
    app.messageRenderer.addMessage(
        elements.chatContainer,
        `❌ **Lỗi kết nối:** ${error.message}`,
        false, formValues.model, formValues.context, errorTimestamp,
        null, customPromptUsed
    );
    app.saveCurrentSession(true);
}
