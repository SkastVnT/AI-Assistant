/**
 * Language translations for ChatBot
 * Supports: Vietnamese (vi) and English (en)
 */

const translations = {
    vi: {
        // Header
        'app.title': '🤖 AI ChatBot Assistant',
        'app.subtitle': 'Hỗ trợ tâm lý, tâm sự và giải pháp đời sống, hỗ trợ lập trình chung',
        
        // Sidebar
        'sidebar.title': '💬 Lịch sử Chat',
        'sidebar.newChat': '+ Mới',
        'sidebar.calculating': 'Đang tính...',
        
        // Controls
        'controls.model': 'Model:',
        'controls.mode': 'Chế độ:',
        'controls.mode.casual': 'Trò chuyện vui vẻ',
        'controls.mode.psychological': 'Tâm lý - Tâm sự',
        'controls.mode.lifestyle': 'Giải pháp đời sống',
        'controls.mode.programming': '💻 Hỗ trợ lập trình',
        'controls.deepThinking': '🧠 Deep Thinking (o1)',
        'controls.download': '📥 Tải chat',
        'controls.imageGen': '🎨 Tạo ảnh',
        'controls.memory': '🧠 AI học tập',
        'controls.clear': '🗑️ Xóa lịch sử',
        
        // Model options
        'model.grok': 'GROK (xAI) - FREE ⭐',
        'model.openai': 'GPT-4o-mini (OpenAI)',
        'model.deepseek': 'DeepSeek (Rẻ nhất)',
        'model.qwen': 'Qwen1.5b (Alibaba Cloud)',
        'model.bloomvn': 'BloomVN-8B API (Tiếng Việt) - FREE',
        'model.local.group': '🖥️ Local Models (FREE - No Internet)',
        'model.local.qwen15': '🖥️ Qwen1.5-1.8B Local',
        'model.local.bloomvn': '🖥️ BloomVN-8B Local',
        'model.local.qwen25': '🖥️ Qwen2.5-14B Local ⭐',
        
        // Initial message
        'chat.welcome': 'Xin chào! Tôi là trợ lý AI của bạn. Tôi có thể giúp gì cho bạn hôm nay? 😊',
        
        // Memory panel
        'memory.title': '📚 Bài học đã lưu (chọn để kích hoạt):',
        'memory.save': '💾 Lưu chat này',
        
        // Loading
        'loading.thinking': 'Đang suy nghĩ...',
        'loading.stop': '⏹️ Dừng lại',
        
        // Input tools
        'tools.googleSearch': '🔍 Google Search',
        'tools.github': 'GitHub',
        'tools.text2img': '🎨 Text2Img',
        'tools.img2img': '🖼️ Img2Img',
        'tools.uploadFiles': '📎 Upload Files',
        'input.placeholder': 'Nhập tin nhắn của bạn... (Shift+Enter để xuống dòng, Ctrl+V để paste)',
        'input.send': 'Gửi',
        
        // Buttons and actions
        'button.copy': '📋 Copy',
        'button.edit': '✏️ Edit',
        'button.delete': '🗑️ Delete',
        'button.regenerate': '🔄 Regenerate',
        
        // Chat list
        'chatList.noChats': 'Chưa có cuộc trò chuyện nào',
        'chatList.newChat': 'Cuộc trò chuyện mới',
        'chatList.untitled': 'No messages',
        
        // Storage info
        'storage.used': 'Đã dùng',
        'storage.available': 'Khả dụng',
        
        // Dark mode button (emoji only, no text needed)
        'darkMode.toggle': '🌙',
        
        // Image generation modal
        'imageGen.title': '🎨 Tạo ảnh bằng AI',
        'imageGen.status.checking': 'Đang kiểm tra Stable Diffusion...',
        'imageGen.tab.text2img': '✍️ Tạo ảnh từ prompt',
        'imageGen.tab.img2img': '🖼️ Tạo ảnh theo hình ảnh',
        'imageGen.model': 'Model Checkpoint:',
        'imageGen.model.loading': 'Đang tải...',
        'imageGen.prompt': 'Prompt (Mô tả ảnh bạn muốn tạo):',
        'imageGen.prompt.placeholder': '1girl, beautiful, detailed face, long hair, cherry blossoms, sunset, masterpiece, best quality',
        'imageGen.negativePrompt': 'Negative Prompt (Những gì KHÔNG muốn có):',
        'imageGen.negativePrompt.placeholder': 'bad quality, blurry, distorted, ugly, worst quality',
        'imageGen.steps': 'Steps',
        'imageGen.stepsHint': '(20-50 khuyến nghị)',
        'imageGen.cfgScale': 'CFG Scale',
        'imageGen.cfgHint': '(7-12 khuyến nghị)',
        'imageGen.width': 'Width:',
        'imageGen.height': 'Height:',
        'imageGen.sampler': 'Sampler:',
        'imageGen.restoreFaces': 'Restore Faces (GFPGAN)',
        'imageGen.hiresfix': 'Hires. Fix (Chất lượng cao)',
        'imageGen.lora': '🎨 Lora Models (Tùy chọn):',
        'imageGen.addLora': '➕ Thêm Lora',
        'imageGen.vae': '🔧 VAE Model:',
        'imageGen.generate': '🎨 Tạo ảnh',
        'imageGen.uploading': 'Đang upload...',
        'imageGen.upload': '📤 Upload ảnh',
        'imageGen.dragDrop': 'Kéo thả ảnh vào đây hoặc click để chọn',
        'imageGen.denoise': 'Denoising Strength:',
        'imageGen.random': '🎲 Random',
        
        // History modal
        'history.title': '📜 Lịch sử chỉnh sửa',
        'history.close': 'Đóng',
        
        // Tooltips
        'tooltip.download': 'Tải xuống lịch sử chat',
        'tooltip.imageGen': 'Tạo ảnh bằng AI',
        'tooltip.memory': 'Quản lý bộ nhớ AI',
        'tooltip.darkMode': 'Toggle Dark Mode',
        'tooltip.googleSearch': 'Tìm kiếm Google',
        'tooltip.github': 'Kết nối GitHub',
        'tooltip.text2img': 'Tạo ảnh từ text prompt (Text2Img)',
        'tooltip.img2img': 'Tạo ảnh từ upload (Img2Img)',
        'tooltip.uploadFiles': 'Upload tài liệu (txt, pdf, doc, code files)',
    },
    
    en: {
        // Header
        'app.title': '🤖 AI ChatBot Assistant',
        'app.subtitle': 'Psychological support, life advice, and programming assistance',
        
        // Sidebar
        'sidebar.title': '💬 Chat History',
        'sidebar.newChat': '+ New',
        'sidebar.calculating': 'Calculating...',
        
        // Controls
        'controls.model': 'Model:',
        'controls.mode': 'Mode:',
        'controls.mode.casual': 'Casual Chat',
        'controls.mode.psychological': 'Psychological Support',
        'controls.mode.lifestyle': 'Life Solutions',
        'controls.mode.programming': '💻 Programming Help',
        'controls.deepThinking': '🧠 Deep Thinking',
        'controls.download': '📥 Download Chat',
        'controls.imageGen': '🎨 Generate Image',
        'controls.memory': '🧠 AI Learning',
        'controls.clear': '🗑️ Clear History',
        
        // Model options
        'model.grok': 'GROK (xAI) - FREE ⭐',
        'model.openai': 'GPT-4o-mini (OpenAI)',
        'model.deepseek': 'DeepSeek (Cheapest)',
        'model.qwen': 'Qwen1.5b (Alibaba Cloud)',
        'model.bloomvn': 'BloomVN-8B API (Vietnamese) - FREE',
        'model.local.group': '🖥️ Local Models (FREE - No Internet)',
        'model.local.qwen15': '🖥️ Qwen1.5-1.8B Local',
        'model.local.bloomvn': '🖥️ BloomVN-8B Local',
        'model.local.qwen25': '🖥️ Qwen2.5-14B Local ⭐',
        
        // Initial message
        'chat.welcome': 'Hello! I am your AI assistant. How can I help you today? 😊',
        
        // Memory panel
        'memory.title': '📚 Saved lessons (click to activate):',
        'memory.save': '💾 Save this chat',
        
        // Loading
        'loading.thinking': 'Thinking...',
        'loading.stop': '⏹️ Stop',
        
        // Input tools
        'tools.googleSearch': '🔍 Google Search',
        'tools.github': 'GitHub',
        'tools.text2img': '🎨 Text2Img',
        'tools.img2img': '🖼️ Img2Img',
        'tools.uploadFiles': '📎 Upload Files',
        'input.placeholder': 'Type your message... (Shift+Enter for new line, Ctrl+V to paste)',
        'input.send': 'Send',
        
        // Buttons and actions
        'button.copy': '📋 Copy',
        'button.edit': '✏️ Edit',
        'button.delete': '🗑️ Delete',
        'button.regenerate': '🔄 Regenerate',
        
        // Chat list
        'chatList.noChats': 'No conversations yet',
        'chatList.newChat': 'New conversation',
        'chatList.untitled': 'No messages',
        
        // Storage info
        'storage.used': 'Used',
        'storage.available': 'Available',
        
        // Dark mode button (emoji only, no text needed)
        'darkMode.toggle': '🌙',
        
        // Image generation modal
        'imageGen.title': '🎨 AI Image Generator',
        'imageGen.status.checking': 'Checking Stable Diffusion...',
        'imageGen.tab.text2img': '✍️ Generate from prompt',
        'imageGen.tab.img2img': '🖼️ Generate from image',
        'imageGen.model': 'Model Checkpoint:',
        'imageGen.model.loading': 'Loading...',
        'imageGen.prompt': 'Prompt (Image description):',
        'imageGen.prompt.placeholder': '1girl, beautiful, detailed face, long hair, cherry blossoms, sunset, masterpiece, best quality',
        'imageGen.negativePrompt': 'Negative Prompt (What you DON\'t want):',
        'imageGen.negativePrompt.placeholder': 'bad quality, blurry, distorted, ugly, worst quality',
        'imageGen.steps': 'Steps',
        'imageGen.stepsHint': '(20-50 recommended)',
        'imageGen.cfgScale': 'CFG Scale',
        'imageGen.cfgHint': '(7-12 recommended)',
        'imageGen.width': 'Width:',
        'imageGen.height': 'Height:',
        'imageGen.sampler': 'Sampler:',
        'imageGen.restoreFaces': 'Restore Faces (GFPGAN)',
        'imageGen.hiresfix': 'Hires. Fix (High quality)',
        'imageGen.lora': '🎨 Lora Models (Optional):',
        'imageGen.addLora': '➕ Add Lora',
        'imageGen.vae': '🔧 VAE Model:',
        'imageGen.generate': '🎨 Generate Image',
        'imageGen.uploading': 'Uploading...',
        'imageGen.upload': '📤 Upload Image',
        'imageGen.dragDrop': 'Drag and drop image here or click to select',
        'imageGen.denoise': 'Denoising Strength:',
        'imageGen.random': '🎲 Random',
        
        // History modal
        'history.title': '📜 Edit History',
        'history.close': 'Close',
        
        // Tooltips
        'tooltip.download': 'Download chat history',
        'tooltip.imageGen': 'Generate image with AI',
        'tooltip.memory': 'Manage AI memory',
        'tooltip.darkMode': 'Toggle Dark Mode',
        'tooltip.googleSearch': 'Google Search',
        'tooltip.github': 'Connect GitHub',
        'tooltip.text2img': 'Generate image from text prompt (Text2Img)',
        'tooltip.img2img': 'Generate image from upload (Img2Img)',
        'tooltip.uploadFiles': 'Upload documents (txt, pdf, doc, code files)',
    }
};

// Export for ES6 modules
export default translations;
