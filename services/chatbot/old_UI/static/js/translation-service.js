/**
 * Translation Service
 * Handles automatic translation of chat titles when switching languages
 */

class TranslationService {
    constructor() {
        this.cache = this.loadCache();
    }

    /**
     * Load translation cache from localStorage
     */
    loadCache() {
        const cached = localStorage.getItem('translation_cache');
        return cached ? JSON.parse(cached) : {};
    }

    /**
     * Save translation cache to localStorage
     */
    saveCache() {
        localStorage.setItem('translation_cache', JSON.stringify(this.cache));
    }

    /**
     * Get cache key
     */
    getCacheKey(text, targetLang) {
        return `${text}|${targetLang}`;
    }

    /**
     * Translate text using backend AI
     */
    async translateWithAI(text, targetLang) {
        const cacheKey = this.getCacheKey(text, targetLang);
        
        // Check cache first
        if (this.cache[cacheKey]) {
            return this.cache[cacheKey];
        }

        try {
            const prompt = targetLang === 'en' 
                ? `Translate this Vietnamese text to English (only return the translation, no explanations): "${text}"`
                : `Translate this English text to Vietnamese (only return the translation, no explanations): "${text}"`;

            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: prompt,
                    model: 'grok',
                    context: 'casual',
                    language: targetLang,
                    deep_thinking: false
                })
            });

            const data = await response.json();
            let translated = data.response.trim();
            
            // Remove quotes if AI added them
            translated = translated.replace(/^["']|["']$/g, '');
            
            // Cache the translation
            this.cache[cacheKey] = translated;
            this.saveCache();
            
            return translated;
        } catch (error) {
            console.error('Translation failed:', error);
            return text; // Return original if translation fails
        }
    }

    /**
     * Simple rule-based translation for common phrases
     */
    quickTranslate(text, targetLang) {
        const translations = {
            vi: {
                'New conversation': 'Cuộc trò chuyện mới',
                'Casual Chat': 'Trò chuyện vui vẻ',
                'Psychological Support': 'Tâm lý - Tâm sự',
                'Life Solutions': 'Giải pháp đời sống',
                'Programming Help': 'Hỗ trợ lập trình',
                'No messages': 'Chưa có tin nhắn',
                'Untitled': 'Chưa có tiêu đề'
            },
            en: {
                'Cuộc trò chuyện mới': 'New conversation',
                'Trò chuyện vui vẻ': 'Casual Chat',
                'Tâm lý - Tâm sự': 'Psychological Support',
                'Giải pháp đời sống': 'Life Solutions',
                'Hỗ trợ lập trình': 'Programming Help',
                'Chưa có tin nhắn': 'No messages',
                'Chưa có tiêu đề': 'Untitled'
            }
        };

        return translations[targetLang][text] || null;
    }

    /**
     * Translate text with quick lookup first, then AI
     */
    async translate(text, targetLang) {
        // Try quick translation first
        const quick = this.quickTranslate(text, targetLang);
        if (quick) {
            return quick;
        }

        // Use AI for custom text
        return await this.translateWithAI(text, targetLang);
    }

    /**
     * Translate all chat titles in localStorage
     */
    async translateChatTitles(targetLang) {
        const chatSessions = localStorage.getItem('chatSessions');
        if (!chatSessions) return;

        const sessions = JSON.parse(chatSessions);
        const sessionIds = Object.keys(sessions);
        
        // Translate titles in batches
        for (const id of sessionIds) {
            const session = sessions[id];
            const originalTitle = session.title;
            
            // Skip if already in target language or is default title
            if (this.isDefaultTitle(originalTitle)) {
                session.title = this.getDefaultTitle(targetLang);
                continue;
            }

            // Translate the title
            session.title = await this.translate(originalTitle, targetLang);
        }

        // Save updated sessions
        localStorage.setItem('chatSessions', JSON.stringify(sessions));
    }

    /**
     * Check if title is a default title
     */
    isDefaultTitle(title) {
        const defaults = [
            'Cuộc trò chuyện mới',
            'New conversation',
            'Chưa có tin nhắn',
            'No messages'
        ];
        return defaults.includes(title);
    }

    /**
     * Get default title for language
     */
    getDefaultTitle(lang) {
        return lang === 'vi' ? 'Cuộc trò chuyện mới' : 'New conversation';
    }
}

// Export singleton instance
export const translationService = new TranslationService();
