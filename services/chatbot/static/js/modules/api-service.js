/**
 * API Service Module
 * Handles all API communications with the backend
 */

export class APIService {
    constructor() {
        this.baseUrl = '';
    }

    /**
     * Send chat message to backend
     */
    async sendMessage(message, model, context, tools = [], deepThinking = false, history = [], files = [], memories = [], abortSignal = null, customPrompt = '', agentConfig = null, thinkingMode = null) {
        let response;
        
        // Get current language from localStorage
        const language = localStorage.getItem('chatbot_language') || 'vi';
        
        // Get thinking mode from global function if not provided
        if (!thinkingMode && window.getThinkingMode) {
            thinkingMode = window.getThinkingMode();
        }
        thinkingMode = thinkingMode || 'instant';
        
        const fetchOptions = {
            method: 'POST',
            signal: abortSignal
        };
        
        // If there are files, use FormData (multipart/form-data)
        if (files && files.length > 0) {
            const formData = new FormData();
            formData.append('message', message);
            formData.append('model', model);
            formData.append('context', context);
            formData.append('tools', JSON.stringify(tools));
            formData.append('deep_thinking', deepThinking);
            formData.append('thinking_mode', thinkingMode);  // Add thinking mode
            formData.append('history', JSON.stringify(history));
            formData.append('memory_ids', JSON.stringify(memories));
            formData.append('language', language);  // Add language
            formData.append('custom_prompt', customPrompt);  // Add custom prompt
            
            // Add agent config if provided
            if (agentConfig) {
                formData.append('agent_config', JSON.stringify(agentConfig));
            }
            
            // Add MCP selected files
            const mcpFiles = window.mcpController ? window.mcpController.getSelectedFilePaths() : [];
            formData.append('mcp_selected_files', JSON.stringify(mcpFiles));

            // Append files
            files.forEach((file) => {
                formData.append('files', file);
            });

            fetchOptions.body = formData;
            response = await fetch('/chat', fetchOptions);
        } else {
            // No files, use JSON
            fetchOptions.headers = {
                'Content-Type': 'application/json'
            };
            // Get MCP selected files
            const mcpFiles = window.mcpController ? window.mcpController.getSelectedFilePaths() : [];
            
            fetchOptions.body = JSON.stringify({
                message: message,
                model: model,
                context: context,
                tools: tools,
                deep_thinking: deepThinking,
                thinking_mode: thinkingMode,  // Add thinking mode
                history: history,
                memory_ids: memories,
                mcp_selected_files: mcpFiles,
                language: language,  // Add language
                custom_prompt: customPrompt,  // Add custom prompt
                agent_config: agentConfig  // Add full agent config
            });
            
            response = await fetch('/chat', fetchOptions);
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Send chat message via SSE streaming with live thinking display
     * 
     * @param {Object} params - Message parameters
     * @param {AbortSignal} abortSignal - Abort signal for cancellation
     * @param {Object} callbacks - Event callbacks: onThinkingStart, onThinking, onThinkingEnd, onChunk, onComplete, onError
     * @returns {Promise<Object>} Final complete response data
     */
    async sendStreamMessage(params, abortSignal = null, callbacks = {}) {
        const language = localStorage.getItem('chatbot_language') || 'vi';
        let thinkingMode = params.thinkingMode;
        if (!thinkingMode && window.getThinkingMode) {
            thinkingMode = window.getThinkingMode();
        }
        thinkingMode = thinkingMode || 'instant';

        const body = {
            message: params.message,
            model: params.model || 'grok',
            context: params.context || 'casual',
            deep_thinking: params.deepThinking || false,
            thinking_mode: thinkingMode,
            history: params.history || [],
            memory_ids: params.memories || [],
            mcp_selected_files: window.mcpController ? window.mcpController.getSelectedFilePaths() : [],
            language: language,
            custom_prompt: params.customPrompt || '',
            tools: params.tools || [],
            skill: params.skill || '',
            skill_auto_route: params.skillAutoRoute !== false ? 'true' : 'false',
            conversation_id: params.conversationId || '',
            generated_images: Array.isArray(params.generatedImages) ? params.generatedImages : [],
            // Thinking-with-Images: explicit signal that the frontend classified
            // this as an image request, so the backend bridge engages reliably
            // regardless of its own keyword router.
            force_image_bridge: params.forceImageBridge || false,
            // Over-Reviewers: generate 3 chart types instead of 1
            over_reviewers: params.overReviewers || false,
        };

        // Forward image-bridge run options (mode-card) into the pipeline request.
        if (params.imageOnly != null) body.image_only = !!params.imageOnly;
        if (params.batchSize != null) body.batch_size = params.batchSize;

        // Include images for vision models (base64 data URLs)
        if (params.images && params.images.length > 0) {
            body.images = params.images;
        }

        // Include per-request model parameter overrides (null = use server defaults)
        if (params.temperature != null) body.temperature = params.temperature;
        if (params.temperatureDeep != null) body.temperature_deep = params.temperatureDeep;
        if (params.maxTokensDeep != null) body.max_tokens_deep = params.maxTokensDeep;
        if (params.topP != null) body.top_p = params.topP;

        const response = await fetch('/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: abortSignal,
        });

        if (!response.ok) {
            // 2026-04-29: read body so the user sees the actual server
            // error (rate limit, auth, validation) instead of a bare
            // "HTTP 500". Body may be JSON or plain text.
            let detail = '';
            try {
                const txt = await response.text();
                if (txt) {
                    try { detail = JSON.parse(txt).error || JSON.parse(txt).message || txt; }
                    catch { detail = txt.slice(0, 500); }
                }
            } catch { /* ignore */ }
            const err = new Error(`HTTP ${response.status}${detail ? ': ' + detail : ''}`);
            err.status = response.status;
            throw err;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let result = null;
        // 2026-04-29: track accumulated assistant text so a mid-stream
        // disconnect can hand the partial back to the UI instead of
        // erasing what was already streamed.
        let _streamedText = '';
        const _wrapChunk = callbacks.onChunk;
        if (_wrapChunk) {
            callbacks.onChunk = (data) => {
                try {
                    if (data && typeof data.content === 'string') _streamedText += data.content;
                    else if (data && typeof data.text === 'string') _streamedText += data.text;
                } catch { /* ignore */ }
                return _wrapChunk(data);
            };
        }

        // currentEvent MUST persist across reader reads. A large SSE frame
        // (e.g. ap_result carrying a multi-MB base64 image) splits its
        // `event:` and `data:` lines across separate network chunks; if this
        // is declared inside the read loop the event name is lost and the
        // frame is dropped — exactly why bridged image results showed a
        // caption but no image. (Mirrors anime-pipeline.js _consumeInlineSSE.)
        let currentEvent = 'message';
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // keep incomplete line

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        currentEvent = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6);
                        try {
                            const data = JSON.parse(dataStr);
                            switch (currentEvent) {
                                case 'metadata':
                                    if (callbacks.onMetadata) callbacks.onMetadata(data);
                                    break;
                                case 'thinking_start':
                                    if (callbacks.onThinkingStart) callbacks.onThinkingStart(data);
                                    break;
                                case 'thinking':
                                    if (callbacks.onThinking) callbacks.onThinking(data);
                                    break;
                                case 'thinking_end':
                                    if (callbacks.onThinkingEnd) callbacks.onThinkingEnd(data);
                                    break;
                                case 'chunk':
                                    if (callbacks.onChunk) callbacks.onChunk(data);
                                    break;
                                case 'complete':
                                    result = data;
                                    if (callbacks.onComplete) callbacks.onComplete(data);
                                    break;
                                case 'suggestions':
                                    if (callbacks.onSuggestions) callbacks.onSuggestions(data);
                                    break;
                                case 'error':
                                    if (callbacks.onError) callbacks.onError(data);
                                    break;
                                default:
                                    // Thinking-with-Images bridge: the chat stream
                                    // forwards the anime pipeline's ap_* frames
                                    // verbatim. Hand them to the renderer via a
                                    // single delegate callback (do NOT rename them).
                                    if (currentEvent.startsWith('ap_') && callbacks.onAnimeEvent) {
                                        callbacks.onAnimeEvent(currentEvent, data);
                                    }
                                    break;
                            }
                        } catch (e) {
                            console.warn('[SSE] Skipped malformed frame:', e?.message || e);
                        }
                        currentEvent = 'message'; // reset
                    }
                }
            }
        } catch (e) {
            if (e.name === 'AbortError') {
                console.log('[SSE] Stream aborted by user');
            } else {
                console.error('[SSE] Stream broken:', e?.message || e,
                    `(partial=${_streamedText.length} chars)`);
                if (callbacks.onError) {
                    callbacks.onError({
                        error: `Connection lost: ${e?.message || e}`,
                        recoverable: false,
                        partial_text: _streamedText,
                    });
                }
                // Don't re-throw if we surfaced via onError — caller
                // already informed; throwing would also fire a generic
                // catch and double-toast the user.
                if (!callbacks.onError) throw e;
            }
        } finally {
            reader.cancel().catch(() => {});
        }

        return result || (_streamedText ? { content: _streamedText, partial: true } : {});
    }

    /**
     * Check local models status
     */
    async checkLocalModelsStatus() {
        try {
            const response = await fetch('/api/local-models-status');
            const data = await response.json();
            return data;
        } catch (error) {
            console.log('Local models check failed:', error);
            return { available: false };
        }
    }

    /**
     * Check Stable Diffusion API status
     */
    async checkSDStatus() {
        try {
            const response = await fetch('/sd-api/status');
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('SD status check failed:', error);
            return { status: 'offline' };
        }
    }

    /**
     * Load Stable Diffusion models
     */
    async loadSDModels() {
        try {
            const response = await fetch('/sd-api/models');
            const data = await response.json();
            return data.models || [];
        } catch (error) {
            console.error('Failed to load SD models:', error);
            return [];
        }
    }

    /**
     * Load samplers
     */
    async loadSamplers() {
        try {
            const response = await fetch('/sd-api/samplers');
            const data = await response.json();
            return data.samplers || [];
        } catch (error) {
            console.error('Failed to load samplers:', error);
            return [];
        }
    }

    /**
     * Load LoRAs
     */
    async loadLoras() {
        try {
            const response = await fetch('/sd-api/loras');
            const data = await response.json();
            return data.loras || [];
        } catch (error) {
            console.error('Failed to load LoRAs:', error);
            return [];
        }
    }

    /**
     * Load VAEs
     */
    async loadVaes() {
        try {
            const response = await fetch('/sd-api/vaes');
            const data = await response.json();
            return data.vaes || [];
        } catch (error) {
            console.error('Failed to load VAEs:', error);
            return [];
        }
    }

    /**
     * Generate image (Text2Img)
     */
    async generateImage(params) {
        // Always enable save_to_storage for MongoDB persistence
        const enhancedParams = {
            ...params,
            save_to_storage: true
        };
        
        const response = await fetch('/api/generate-image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(enhancedParams)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Generate image from image (Img2Img)
     */
    async generateImg2Img(params) {
        // Always enable save_to_storage for MongoDB persistence
        const enhancedParams = {
            ...params,
            save_to_storage: true
        };
        
        const response = await fetch('/api/img2img', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(enhancedParams)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Interrogate image (extract tags)
     */
    async interrogateImage(base64Image, model = 'deepdanbooru') {
        const response = await fetch('/sd-api/interrogate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image: base64Image,
                model: model
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * List memories
     */
    async listMemories() {
        const response = await fetch('/api/memory/list');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Save memory
     */
    async saveMemory(title, content, images = []) {
        const response = await fetch('/api/memory/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: title,
                content: content,
                images: images
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Delete memory
     */
    async deleteMemory(memoryId) {
        const response = await fetch(`/api/memory/delete/${memoryId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Load memory by ID
     */
    async loadMemory(memoryId) {
        const response = await fetch(`/api/memory/load/${memoryId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Get storage images list
     */
    async getStorageImages() {
        try {
            const response = await fetch('/api/storage/images');
            const data = await response.json();
            return data.images || [];
        } catch (error) {
            console.error('Failed to load storage images:', error);
            return [];
        }
    }

    /**
     * Delete storage image
     */
    async deleteStorageImage(filename) {
        const response = await fetch('/api/storage/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: filename
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }
}
