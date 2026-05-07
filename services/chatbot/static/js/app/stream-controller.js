/**
 * stream-controller.js — owns the SSE lifecycle for a single in-flight request.
 *
 * Hard rules:
 *  - Each send generates a fresh streamId.
 *  - We drop any frame whose payload streamId or conversation_id does not match
 *    the currently active context. This makes late frames from a stopped stream
 *    impossible to corrupt the UI.
 *  - On `complete` or `error` we always return to `idle` and refocus the input.
 */

import { streamChat } from './api.js';
import { appState, setStatus, newStreamId, patch } from './state.js';
import { appendChunk, finalizeStreaming, renderMessage } from './chat-renderer.js';
import { chatStore } from './chat-store.js';
import { toast } from './toast.js';
import { dom } from './dom.js';

let _abort = null;

function _matchesActive(data) {
    if (!data) return true;
    const sid = data.stream_id || data.streamId || data.request_id || data.requestId;
    const cid = data.conversation_id || data.conversationId;
    if (sid && appState.currentStreamId && sid !== appState.currentStreamId) return false;
    if (cid && appState.currentConversationId && cid !== appState.currentConversationId) return false;
    return true;
}

function _refocusComposer() {
    const inp = dom('composerInput');
    if (inp) {
        inp.value = '';
        inp.style.height = 'auto';
        try { inp.focus(); } catch {}
    }
}

export const streamController = {
    isStreaming() {
        return appState.status === 'streaming' || appState.status === 'stopping';
    },

    async send({ message, images, tools, conversationId }) {
        if (this.isStreaming()) {
            console.warn('[stream] send called while streaming; ignored');
            return;
        }
        if (!message || !message.trim()) return;

        const streamId = newStreamId();
        patch({
            currentStreamId: streamId,
            currentConversationId: conversationId || appState.currentConversationId,
        });
        setStatus('streaming');

        // Optimistic user message
        const userMsg = {
            id: 'u_' + Date.now(),
            role: 'user',
            content: message,
            images: images || [],
            createdAt: Date.now(),
        };
        chatStore.appendMessage(userMsg);
        const list = dom('messageList');
        if (list) {
            const empty = list.querySelector('.chat__empty');
            if (empty) empty.remove();
            list.appendChild(renderMessage(userMsg));
            list.scrollTop = list.scrollHeight;
        }

        // Reserve assistant placeholder rendered by appendChunk on first frame.
        const assistantMsg = {
            id: 'a_' + Date.now(),
            role: 'assistant',
            content: '',
            images: [],
            createdAt: Date.now(),
            status: 'streaming',
        };
        chatStore.appendMessage(assistantMsg);

        const language = (localStorage.getItem('chatbot_language') || 'vi');
        const payload = {
            message,
            model: 'grok',
            context: 'casual',
            thinking_mode: 'instant',
            history: [],
            language,
            tools: tools || [],
            conversation_id: appState.currentConversationId || '',
            generated_images: [],
        };
        if (images && images.length) payload.images = images;

        _abort = new AbortController();
        let assembled = '';

        try {
            await streamChat(payload, {
                streamId,
                signal: _abort.signal,
                onEvent: ({ event, data }) => {
                    if (!_matchesActive(data)) return;
                    switch (event) {
                        case 'metadata':
                            // backend may reveal the canonical conversation_id here
                            if (data.conversation_id && !appState.currentConversationId) {
                                patch({ currentConversationId: data.conversation_id });
                                chatStore.cache.setLast(data.conversation_id);
                            }
                            break;
                        case 'chunk': {
                            const t = data.content || data.text || '';
                            if (t) { assembled += t; appendChunk(t); }
                            break;
                        }
                        case 'complete': {
                            const finalText = data.response || data.content || assembled;
                            const finalImages = data.images || data.generated_images || [];
                            finalizeStreaming(finalText, { images: finalImages });
                            chatStore.replaceLastAssistant({
                                content: finalText,
                                images: finalImages,
                                status: 'done',
                            });
                            // expose for gallery refresh
                            document.dispatchEvent(new CustomEvent('chat:complete', { detail: { data } }));
                            break;
                        }
                        case 'error': {
                            const msg = data.error || data.message || 'Stream error';
                            toast.error(msg);
                            chatStore.replaceLastAssistant({ content: assembled, status: 'error' });
                            break;
                        }
                        case 'thinking_start':
                        case 'thinking':
                        case 'thinking_end':
                        case 'suggestions':
                            // not surfaced in the minimal shell yet
                            break;
                    }
                },
            });
            setStatus('idle');
            _refocusComposer();
        } catch (e) {
            if (e.name === 'AbortError') {
                chatStore.replaceLastAssistant({ content: assembled, status: 'aborted' });
                setStatus('idle');
            } else {
                console.error('[stream] failed', e);
                toast.error('Chat failed: ' + (e.message || e));
                chatStore.replaceLastAssistant({ content: assembled || '', status: 'error' });
                setStatus('error');
                setTimeout(() => { if (appState.status === 'error') setStatus('idle'); }, 1500);
            }
            _refocusComposer();
        } finally {
            _abort = null;
            patch({ currentStreamId: null });
        }
    },

    stop() {
        if (!_abort) return;
        setStatus('stopping');
        try { _abort.abort(); } catch {}
    },
};
