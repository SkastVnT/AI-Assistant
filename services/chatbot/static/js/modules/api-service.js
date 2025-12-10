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
    async sendMessage(message, model, context, tools = [], deepThinking = false, history = [], files = [], memories = [], abortSignal = null, customPrompt = '') {
        let response;
        
        // Get current language from localStorage
        const language = localStorage.getItem('chatbot_language') || 'vi';
        
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
            formData.append('history', JSON.stringify(history));
            formData.append('memory_ids', JSON.stringify(memories));
            formData.append('language', language);  // Add language
            formData.append('custom_prompt', customPrompt);  // Add custom prompt

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
            fetchOptions.body = JSON.stringify({
                message: message,
                model: model,
                context: context,
                tools: tools,
                deep_thinking: deepThinking,
                history: history,
                memory_ids: memories,
                language: language,  // Add language
                custom_prompt: customPrompt  // Add custom prompt
            });
            
            response = await fetch('/chat', fetchOptions);
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
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
        const response = await fetch('/api/memory/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                memory_id: memoryId
            })
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
