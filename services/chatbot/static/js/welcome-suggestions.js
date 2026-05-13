document.addEventListener('DOMContentLoaded', () => {
        // Welcome suggestions — random pool, 4 picked each load
        (function initWelcomeSuggestions() {
            const POOL = [
                // ── Giải thích ──────────────────────────────────────────
                { icon: 'lightbulb', label: 'Giải thích', text: 'AI hoạt động thế nào?', msg: 'Giải thích cách hoạt động của AI một cách đơn giản' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'Blockchain là gì?', msg: 'Giải thích blockchain và ứng dụng thực tế của nó' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'Quantum computing là gì?', msg: 'Giải thích quantum computing theo cách dễ hiểu nhất' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'Tại sao trời xanh?', msg: 'Giải thích tại sao bầu trời có màu xanh theo khoa học' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'Cách hoạt động của LLM', msg: 'Giải thích cách hoạt động của mô hình ngôn ngữ lớn (LLM) như GPT' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'DNA và protein', msg: 'Giải thích đơn giản DNA mã hóa thành protein như thế nào' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'Tại sao máy bay bay được?', msg: 'Giải thích nguyên lý khí động học giúp máy bay bay được' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'Internet hoạt động thế nào?', msg: 'Giải thích cách Internet hoạt động từ đầu đến cuối' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'Tại sao ngủ mơ?', msg: 'Giải thích khoa học tại sao chúng ta mơ khi ngủ' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'Sóng điện từ là gì?', msg: 'Giải thích sóng điện từ và các ứng dụng thực tế' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'Tại sao nước đóng băng ở 0°C?', msg: 'Giải thích ở mức phân tử tại sao nước đóng băng ở 0 độ C' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'GPT vs Gemini khác nhau gì?', msg: 'So sánh GPT và Gemini: kiến trúc, điểm mạnh và yếu' },
                { icon: 'lightbulb', label: 'Giải thích', text: 'Tại sao mặt trời không tắt?', msg: 'Giải thích phản ứng hạt nhân giúp mặt trời duy trì nhiệt lượng' },

                // ── Viết code / Debug ────────────────────────────────────
                { icon: 'code-2', label: 'Viết code', text: 'Python quicksort', msg: 'Viết một function Python để sort mảng bằng quicksort' },
                { icon: 'code-2', label: 'Viết code', text: 'REST API với FastAPI', msg: 'Tạo một REST API đơn giản với FastAPI và Python' },
                { icon: 'code-2', label: 'Viết code', text: 'React todo app', msg: 'Viết một todo app đơn giản bằng React hooks' },
                { icon: 'code-2', label: 'Viết code', text: 'SQL query tối ưu', msg: 'Viết câu SQL query để lấy top 10 sản phẩm bán chạy nhất' },
                { icon: 'code-2', label: 'Debug code', text: 'Fix lỗi Python async', msg: 'Giải thích và fix lỗi thường gặp khi dùng async/await trong Python' },
                { icon: 'code-2', label: 'Viết code', text: 'Web scraper Python', msg: 'Viết script Python để scrape dữ liệu từ một trang web bằng BeautifulSoup' },
                { icon: 'code-2', label: 'Viết code', text: 'Login form với React', msg: 'Tạo login form với React, validation và error handling' },
                { icon: 'code-2', label: 'Viết code', text: 'Gửi email bằng Python', msg: 'Viết code Python để gửi email tự động qua SMTP' },
                { icon: 'code-2', label: 'Debug code', text: 'TypeError là gì?', msg: 'Giải thích các loại lỗi TypeError phổ biến trong JavaScript và cách fix' },
                { icon: 'code-2', label: 'Viết code', text: 'Pagination trong SQL', msg: 'Viết SQL query hỗ trợ pagination với LIMIT và OFFSET' },
                { icon: 'code-2', label: 'Viết code', text: 'Docker Compose cơ bản', msg: 'Viết file docker-compose.yml cho app Python + PostgreSQL' },
                { icon: 'code-2', label: 'Viết code', text: 'Infinite scroll React', msg: 'Implement infinite scroll trong React bằng IntersectionObserver' },
                { icon: 'code-2', label: 'Viết code', text: 'Regex tìm email', msg: 'Viết regex Python để validate và tìm địa chỉ email trong văn bản' },
                { icon: 'code-2', label: 'Viết code', text: 'Debounce function JS', msg: 'Giải thích và viết hàm debounce trong JavaScript' },
                { icon: 'code-2', label: 'Viết code', text: 'Binary search', msg: 'Viết thuật toán binary search bằng Python với giải thích từng bước' },
                { icon: 'code-2', label: 'Viết code', text: 'JWT authentication', msg: 'Implement JWT authentication với FastAPI và Python' },
                { icon: 'code-2', label: 'Viết code', text: 'Drag and drop HTML', msg: 'Tạo drag-and-drop list đơn giản thuần JavaScript không dùng thư viện' },
                { icon: 'code-2', label: 'Viết code', text: 'Chatbot đơn giản Python', msg: 'Viết chatbot đơn giản bằng Python sử dụng API OpenAI' },
                { icon: 'code-2', label: 'Debug code', text: 'CORS error là gì?', msg: 'Giải thích CORS error và cách fix trong FastAPI/Express' },
                { icon: 'code-2', label: 'Viết code', text: 'Animation CSS thuần', msg: 'Viết animation CSS cho button hover và loading spinner' },
                { icon: 'code-2', label: 'Viết code', text: 'Rate limiter middleware', msg: 'Implement rate limiter middleware cho Express.js' },
                { icon: 'code-2', label: 'Viết code', text: 'File upload API', msg: 'Viết API upload file ảnh với FastAPI, validate type và size' },

                // ── Tạo ảnh ──────────────────────────────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl tại hoàng hôn', msg: 'Tạo ảnh anime một cô gái ngồi bên cửa sổ, ánh hoàng hôn, chi tiết cao' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cảnh rừng fantasy', msg: 'Tạo ảnh cảnh rừng fantasy với ánh sáng thần tiên, phong cách anime' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Thành phố cyberpunk đêm', msg: 'Tạo ảnh thành phố cyberpunk về đêm, mưa, ánh đèn neon, phong cách anime' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái mùa đông', msg: 'Tạo ảnh anime cô gái mặc áo len, mùa đông, tuyết rơi, ấm áp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Samurai dưới trăng', msg: 'Tạo ảnh anime samurai đứng dưới ánh trăng, hoa anh đào rơi' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái bên biển', msg: 'Tạo ảnh anime cô gái đứng trên bãi biển lúc bình minh, gió thổi tóc' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Phù thủy trong rừng', msg: 'Tạo ảnh anime một phù thủy trẻ trong rừng đêm với ánh phép thuật' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Thành phố cổ đại Nhật', msg: 'Tạo ảnh phong cách anime đường phố cổ Nhật Bản mùa hoa anh đào' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Không gian vũ trụ anime', msg: 'Tạo ảnh anime cô gái nhìn ra cửa sổ tàu vũ trụ, thiên hà đẹp phía sau' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái trong thư viện', msg: 'Tạo ảnh anime cô gái đang đọc sách trong thư viện cổ, ánh nến ấm áp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime chibi dễ thương', msg: 'Tạo ảnh chibi anime dễ thương, màu sắc pastel, phong cách cute' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Làng quê mùa hè', msg: 'Tạo ảnh phong cảnh làng quê Nhật Bản mùa hè, cánh đồng lúa, bầu trời xanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái với mèo', msg: 'Tạo ảnh anime cô gái ngồi ở quán café, con mèo trên đùi, buổi chiều ấm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Ninja trong bóng tối', msg: 'Tạo ảnh anime ninja đứng trên mái nhà đêm tối, thành phố bên dưới' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cảnh tuyết rơi đêm', msg: 'Tạo ảnh anime cảnh đêm tuyết rơi nhẹ, đường phố vắng, đèn đường ấm áp' },
                // ── Tạo ảnh — Cô gái anime (50 mẫu mở rộng) ──────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc hồng sakura', msg: 'Tạo ảnh anime cô gái tóc hồng dài ngồi dưới cây sakura, cánh hoa rơi nhẹ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái mặc đồng phục học sinh', msg: 'Tạo ảnh anime cô gái mặc đồng phục học sinh đứng dưới mưa, cầm ô trong suốt' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái phép thuật ánh sáng', msg: 'Tạo ảnh anime magical girl với phép thuật ánh sáng vàng, váy rườm rà, đôi mắt phát sáng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái quán trà cổ Nhật', msg: 'Tạo ảnh anime cô gái mặc kimono rót trà trong quán trà cổ điển Nhật Bản' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái mèo catgirl', msg: 'Tạo ảnh anime catgirl dễ thương, tai mèo, đuôi mèo, mắt to ngây thơ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái chiến binh fantasy', msg: 'Tạo ảnh anime cô gái chiến binh mặc giáp bạc, kiếm lớn, đứng trên vách đá' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc bạch kim', msg: 'Tạo ảnh anime cô gái tóc bạch kim dài, mắt tím, áo trắng bay trong gió' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái dưới ánh đèn đường', msg: 'Tạo ảnh anime cô gái đứng dưới đèn đường mùa thu, lá rơi xung quanh, buổi tối lạnh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái thám tử áo trench', msg: 'Tạo ảnh anime cô gái thám tử mặc áo trench coat, đứng trong mưa thành phố đêm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái elf rừng xanh', msg: 'Tạo ảnh anime cô gái elf tai nhọn, áo lá cây, giữa khu rừng xanh huyền bí' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc đen mắt đỏ gothic', msg: 'Tạo ảnh anime cô gái gothic tóc đen dài, mắt đỏ, váy đen ren, lâu đài tối' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái nhạc sĩ violin', msg: 'Tạo ảnh anime cô gái chơi violin trên sân thượng dưới ánh trăng tròn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái idol sân khấu', msg: 'Tạo ảnh anime idol cô gái trên sân khấu, ánh đèn concert, confetti rơi' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái dưới biển', msg: 'Tạo ảnh anime cô gái dưới đáy biển sâu, ánh sáng xanh lam, cá nhiều màu bơi xung quanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc xanh băng giá', msg: 'Tạo ảnh anime cô gái tóc xanh băng lạnh, áo trắng, cảnh tuyết nguyên sơ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái phù thủy mũ cao', msg: 'Tạo ảnh anime cô gái phù thủy mũ cao, áo đen, cầm gậy phép thuật, trăng sau lưng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc đỏ lửa', msg: 'Tạo ảnh anime cô gái tóc đỏ rực, mắt hổ phách, đứng giữa cánh đồng hoa hướng dương' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái mặc yukata lễ hội', msg: 'Tạo ảnh anime cô gái mặc yukata hoa cúc tại lễ hội mùa hè, pháo hoa đêm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái ngủ trong hoa', msg: 'Tạo ảnh anime cô gái ngủ giữa đồng hoa lavender tím, bướm bay xung quanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái cyberpunk neon', msg: 'Tạo ảnh anime cô gái phong cách cyberpunk, tóc tím neon, kính AR, đường phố đêm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc vàng mắt xanh', msg: 'Tạo ảnh anime cô gái tóc vàng dài, mắt xanh dương, váy trắng ở cánh đồng cỏ xanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái y tá cute', msg: 'Tạo ảnh anime cô gái y tá đồng phục trắng, dễ thương, nụ cười ấm áp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái vũ công ballet', msg: 'Tạo ảnh anime cô gái múa ballet trên sân khấu nhỏ, ánh đèn spot, váy tutu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái đọc sách trên cây', msg: 'Tạo ảnh anime cô gái ngồi trên cành cây lớn đọc sách, ánh nắng chiều xuyên qua lá' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc bím twin-tail', msg: 'Tạo ảnh anime cô gái twin-tail tóc đen, đồng phục thủy thủ, vui vẻ dưới nắng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái bên cửa sổ mưa', msg: 'Tạo ảnh anime cô gái ngồi bên cửa sổ nhìn mưa rơi, ly cà phê bốc khói, buồn nhẹ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái thần rừng', msg: 'Tạo ảnh anime cô gái thần rừng, tóc lá cây, mắt xanh lá, ngồi trên gốc cây cổ thụ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái robot mecha', msg: 'Tạo ảnh anime cô gái mặc giáp mecha robot trắng bạc, cảnh chiến trường tương lai' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái mặc áo lụa cung đình', msg: 'Tạo ảnh anime cô gái mặc áo lụa cung đình Trung Hoa, đứng trong vườn hoa đào' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái cưỡi rồng', msg: 'Tạo ảnh anime cô gái tóc bạch kim cưỡi rồng trắng bay trên mây, bầu trời hoàng hôn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tắm suối hot spring', msg: 'Tạo ảnh anime cô gái trong onsen lộ thiên mùa đông, tuyết rơi nhẹ, mặt đỏ hồng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tiên nữ cánh bướm', msg: 'Tạo ảnh anime tiên nữ nhỏ xinh, cánh bướm phát sáng, ngồi trên bông hoa khổng lồ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc trắng mắt vàng', msg: 'Tạo ảnh anime cô gái tóc trắng dài, mắt vàng hổ phách, áo đen giữa cánh đồng tuyết' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái stargazer', msg: 'Tạo ảnh anime cô gái nằm trên cỏ nhìn bầu trời đầy sao, dải ngân hà rõ nét' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái quán cà phê maid', msg: 'Tạo ảnh anime cô gái maid café dễ thương, tạp dề ren, mang khay bánh, mỉm cười' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc tím bên hồ', msg: 'Tạo ảnh anime cô gái tóc tím ngắn ngồi bên hồ kính, phản chiếu bầu trời xanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái archer cung thủ', msg: 'Tạo ảnh anime cô gái cung thủ mặc áo lữ hành, giương cung trong rừng lá vàng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái bếp núc waifu', msg: 'Tạo ảnh anime cô gái đeo tạp dề hoa, đang nấu ăn trong bếp sáng đẹp, mỉm cười' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc dài bay gió', msg: 'Tạo ảnh anime cô gái tóc đen dài bay trong gió trên đỉnh đồi, váy trắng, bầu trời xanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái nữ thần biển cả', msg: 'Tạo ảnh anime nữ thần biển cả, tóc xanh lam, vảy cá, ngồi trên đá giữa biển' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái mặc áo dài Việt Nam', msg: 'Tạo ảnh anime cô gái mặc áo dài trắng Việt Nam, nón lá, đứng bên hồ sen' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái bắn súng action', msg: 'Tạo ảnh anime cô gái tóc bạch kim cầm súng, tư thế chiến đấu, background khói lửa' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái angel thiên thần', msg: 'Tạo ảnh anime thiên thần cô gái, cánh trắng lớn, áo trắng, hào quang vàng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái cafe buổi sáng', msg: 'Tạo ảnh anime cô gái ngồi uống cà phê buổi sáng sớm, ánh nắng vàng, cảnh phố nhỏ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc hai màu split-dye', msg: 'Tạo ảnh anime cô gái tóc nửa trắng nửa đen, mắt dị màu, phong cách bí ẩn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái chạy trên đường ray', msg: 'Tạo ảnh anime cô gái chạy trên đường ray hiu quạnh, cánh đồng xanh hai bên, hoàng hôn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái lolita gothic trắng', msg: 'Tạo ảnh anime cô gái lolita váy trắng ren, dù nhỏ trắng, vườn hoa hồng trắng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái thủy sư đội trưởng', msg: 'Tạo ảnh anime cô gái thủy thủ đội trưởng, áo vest trắng, mũ đội trưởng, trên tàu chiến' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái thức đêm lập trình', msg: 'Tạo ảnh anime cô gái hacker coder thức đêm, ánh màn hình xanh, hoodie, mì tôm bên cạnh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái fox girl kitsune', msg: 'Tạo ảnh anime kitsune cô gái, 9 đuôi cáo trắng, kimono đỏ, đứng trong đền Torii' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái bên pháo hoa', msg: 'Tạo ảnh anime cô gái mặc yukata nhìn pháo hoa đêm lễ hội, mắt lấp lánh phản chiếu' },

                // ── Tạo ảnh — Honkai Star Rail Characters ─────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Firefly HSR — bộ giáp SAM', msg: 'Tạo ảnh anime Firefly (Honkai Star Rail) trong bộ giáp SAM đỏ đen, nền vũ trụ, tư thế chiến đấu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Firefly HSR — váy cánh bướm', msg: 'Tạo ảnh anime Firefly (HSR) mặc váy đen cánh bướm cháy, tóc đỏ nâu dài, đôi mắt cam cháy' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Stelle HSR — trailblazer nữ', msg: 'Tạo ảnh anime Stelle (HSR Trailblazer) tóc xám, mắt vàng, áo jacket đen, biểu cảm tự tin' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Stelle HSR — chibi cute', msg: 'Tạo ảnh chibi anime Stelle (Honkai Star Rail) dễ thương, màu pastel, tư thế vui vẻ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Silver Wolf HSR — hacker', msg: 'Tạo ảnh anime Silver Wolf (HSR) ngồi gõ máy tính, ánh màn hình xanh lá, biểu cảm thách thức' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Silver Wolf HSR — tóc bạch kim', msg: 'Tạo ảnh anime Silver Wolf (HSR) tóc bạch kim dài, mắt xám, kính mát trên đầu, áo hoodie' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Huohuo HSR — fox girl', msg: 'Tạo ảnh anime Huohuo (HSR) cô gái cáo, tóc xanh lá dài, tai cáo, đuôi cáo, áo truyền thống Trung Hoa' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Huohuo HSR — chữa lành', msg: 'Tạo ảnh anime Huohuo (HSR) đang phát ánh sáng chữa lành xanh lá, biểu cảm hiền dịu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Kafka HSR — bí ẩn', msg: 'Tạo ảnh anime Kafka (HSR) tóc đen tím dài, mắt tím, áo vest tối màu, biểu cảm bí ẩn sexy' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Kafka HSR — dưới ánh đèn', msg: 'Tạo ảnh anime Kafka (Honkai Star Rail) đứng dưới ánh đèn đường tím, tóc dài bay, tư thế thanh lịch' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Sparkle HSR — harlequin', msg: 'Tạo ảnh anime Sparkle (HSR) trang phục harlequin trắng đỏ đen, đôi mắt hồng, biểu cảm nghịch ngợm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Lynx HSR — mùa đông', msg: 'Tạo ảnh anime Lynx Landau (HSR) tóc vàng ngắn, mũ lông, áo choàng mùa đông xanh, tuyết rơi' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Robin HSR — ca sĩ', msg: 'Tạo ảnh anime Robin (HSR) trên sân khấu ánh đèn rực rỡ, đôi cánh trắng xòe, micro trên tay' },
                { icon: 'image', label: 'Tạo ảnh', text: 'The Herta HSR — phù thủy', msg: 'Tạo ảnh anime The Herta (HSR) tóc xám dài, mắt tím, mũ phù thủy đen, tư thế kiêu ngạo' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Hyacine HSR — twin drill', msg: 'Tạo ảnh anime Hyacine (HSR) tóc hồng xanh drill, mắt xanh ngọc, váy đỏ xinh đẹp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cyrene HSR — thần thánh', msg: 'Tạo ảnh anime Cyrene (HSR) vương miện hoa, áo trắng, tóc hồng, đôi mắt kim cương, vầng sáng sau lưng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Castorice HSR — bóng tối', msg: 'Tạo ảnh anime Castorice (HSR) tóc trắng dài, áo đen, biểu cảm nghiêm lạnh, bóng tối xung quanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Aglaea HSR — ánh sáng', msg: 'Tạo ảnh anime Aglaea (HSR) trang phục vàng rực, đôi mắt vàng, sợi chỉ vàng quấn quanh tay' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Phainon HSR — chiến thần', msg: 'Tạo ảnh anime Phainon (HSR) giáp đen vàng hùng mạnh, tư thế chiến đấu oai vệ, nền hoàng hôn đỏ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'HSR — group shot 4 characters', msg: 'Tạo ảnh anime 4 nhân vật HSR cùng đứng: Stelle, Firefly, Silver Wolf, Kafka — phong cách poster chính thức' },

                // ── Tạo ảnh — Genshin Impact Characters ────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Hu Tao Genshin — lễ hội ma', msg: 'Tạo ảnh anime Hu Tao (Genshin) tóc nâu đuôi bím, mặc đồ lễ hội đêm ma quỷ, ánh lửa cam' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Raiden Shogun — sấm sét', msg: 'Tạo ảnh anime Raiden Shogun (Genshin) tóc tím dài, sấm sét xung quanh, tư thế hoàng gia, kiếm nhật' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Ganyu — tuyết và hoa', msg: 'Tạo ảnh anime Ganyu (Genshin) tóc xanh dài, sừng dê nhỏ, cánh đồng tuyết, ánh sáng xanh lạnh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Yelan Genshin — điệu đà', msg: 'Tạo ảnh anime Yelan (Genshin) tóc xanh đen, trang phục bó sát, tư thế tự tin gợi cảm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Furina Genshin — nước', msg: 'Tạo ảnh anime Furina (Genshin) tóc xanh trắng, bong bóng nước quanh người, biểu cảm kịch tính' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Nahida Genshin — thần nhỏ', msg: 'Tạo ảnh anime Nahida (Genshin) nhỏ bé dễ thương, tai nhọn, ánh xanh lá, ngồi trên lá khổng lồ' },

                // ── Tạo ảnh — Arknights ─────────────────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Surtr Arknights — kiếm lửa', msg: 'Tạo ảnh anime Surtr (Arknights) sừng đỏ, tóc đỏ, kiếm lửa rực, biểu cảm lạnh lùng nguy hiểm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Skadi Arknights — biển sâu', msg: 'Tạo ảnh anime Skadi (Arknights) tóc xanh dài, áo giáp xanh đại dương, kiếm dài, bên bờ biển' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Exusiai Arknights — thiên thần', msg: 'Tạo ảnh anime Exusiai (Arknights) tóc vàng, cánh thiên thần nhỏ, tay cầm táo, biểu cảm vui vẻ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'W Arknights — bí ẩn', msg: 'Tạo ảnh anime W (Arknights) tóc xám, biểu cảm điên loạn vui, bom xung quanh, phong cách tối tăm' },

                // ── Tạo ảnh — Phong cách & Hiệu ứng Đặc Biệt ───────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Doll eyes — iris rực rỡ', msg: 'Tạo ảnh anime cô gái close-up khuôn mặt, đôi mắt như búp bê iris màu tím rực rỡ, highlight ánh sáng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Doll eyes — iris xanh ngọc', msg: 'Tạo ảnh anime cô gái mắt iris xanh ngọc như thủy tinh, phản chiếu ánh sáng, cận cảnh khuôn mặt' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Doll eyes — iris đỏ ma quái', msg: 'Tạo ảnh anime cô gái mắt iris đỏ tươi, phong cách vampire, ánh đêm tối bí ẩn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Mắt ngủ droop half-close', msg: 'Tạo ảnh anime cô gái mắt lim dim buồn ngủ, má hồng nhẹ, nền mờ ấm áp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Mắt khóc — nước mắt lóng lánh', msg: 'Tạo ảnh anime cô gái mắt đỏ hoe, nước mắt chực rơi, biểu cảm buồn đẹp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Mắt nhìn lên (looking up)', msg: 'Tạo ảnh anime cô gái ngước mắt nhìn lên, ánh mắt trong veo, nền bokeh mềm mại' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tai hồ ly 9 đuôi', msg: 'Tạo ảnh anime cô gái kitsune 9 đuôi trắng như tuyết, kimono trắng đỏ, đứng trong rừng đêm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tai thỏ bunny', msg: 'Tạo ảnh anime bunny girl, tai thỏ trắng dài, váy ngắn pastel, biểu cảm ngây thơ dễ thương' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tai mèo đen', msg: 'Tạo ảnh anime neko girl tai mèo đen, mắt vàng sáng, áo len cổ lọ đen, đêm mưa' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái cánh thiên thần', msg: 'Tạo ảnh anime cô gái cánh thiên thần trắng lớn, váy trắng dài, ánh sáng thần thánh từ trên cao' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái cánh quỷ succubus', msg: 'Tạo ảnh anime succubus cánh quỷ đen, sừng nhỏ, tóc đỏ đen, ánh nến đỏ huyền bí' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tóc gradient rainbow', msg: 'Tạo ảnh anime cô gái tóc dài chuyển màu cầu vồng, nền trắng sạch, ánh sáng studio' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái underwater', msg: 'Tạo ảnh anime cô gái dưới nước, bong bóng khí quanh người, ánh sáng xuyên nước màu lam' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái trong hoa nở', msg: 'Tạo ảnh anime cô gái bao quanh bởi hoa sakura trắng hồng nở rộ, nền mờ dreamy' },

                // ── Tạo ảnh — Cảnh Quan Anime Phong Cách ───────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Thành phố nổi trên mây', msg: 'Tạo ảnh phong cách Ghibli thành phố cổ nổi trên những đám mây trắng, ánh bình minh vàng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Rừng nấm phát sáng đêm', msg: 'Tạo ảnh anime cảnh rừng nấm khổng lồ phát sáng xanh tím, đêm kỳ bí, Ghibli style' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Đường ray tàu bay trên mây', msg: 'Tạo ảnh anime đường ray tàu hỏa trên cao giữa những đám mây, hoàng hôn cam đỏ, Ghibli' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Lâu đài băng tuyết', msg: 'Tạo ảnh anime lâu đài băng tuyết lấp lánh dưới ánh trăng, rừng tuyết xung quanh, mùa đông' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cảng biển cổ điển Japan', msg: 'Tạo ảnh anime phong cảnh cảng biển Nhật cổ, thuyền gỗ, đèn lồng đỏ, hoàng hôn đẹp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Đồng cỏ dưới cầu vồng kép', msg: 'Tạo ảnh anime cánh đồng cỏ xanh bao la, cầu vồng kép sau cơn mưa, ánh sáng dịu nhẹ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Thác nước trong rừng cổ', msg: 'Tạo ảnh anime thác nước hùng vĩ trong rừng cây cổ thụ, tảng đá phủ rêu, ánh sáng xanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Phố đêm Tokyo neon', msg: 'Tạo ảnh anime phố đêm Tokyo với đèn neon Nhật rực rỡ, mưa, mặt đường phản chiếu ánh đèn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Đảo nhỏ giữa đại dương', msg: 'Tạo ảnh anime đảo nhỏ xanh mướt giữa biển xanh ngọc, nhà gỗ nhỏ, mây trắng nhẹ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Hang động crystal', msg: 'Tạo ảnh anime hang động tinh thể phát sáng tím xanh, ánh phản chiếu huyền ảo' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cánh đồng hoa lavender', msg: 'Tạo ảnh anime cánh đồng hoa lavender tím bao la, hoàng hôn vàng hồng, cô gái nhỏ phía xa' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Vườn trà mùa thu Nhật', msg: 'Tạo ảnh anime vườn trà Nhật Bản mùa thu, lá đỏ vàng rơi, hàng rào tre, ánh sáng ấm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Thư viện ma thuật cổ', msg: 'Tạo ảnh anime thư viện ma thuật khổng lồ, sách bay lơ lửng, cầu thang xoắn, nến lơ lửng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Đại dương trên bầu trời', msg: 'Tạo ảnh anime surreal đại dương với cá voi bay giữa trời xanh, đảo nhỏ trên mây, dreamy' },

                // ── Tạo ảnh — Trang Phục & Outfit ──────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái mặc qipao đỏ', msg: 'Tạo ảnh anime cô gái mặc qipao đỏ thêu hoa, tóc đen búi, đứng trong sân nhà Trung Hoa cổ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái hanbok Hàn Quốc', msg: 'Tạo ảnh anime cô gái mặc hanbok Hàn Quốc màu pastel, nền hoa anh đào, dịu dàng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái mặc áo dài Việt Nam', msg: 'Tạo ảnh anime phong cách cô gái mặc áo dài Việt Nam trắng, đứng dưới bóng liễu, nhẹ nhàng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái gothic lolita đen', msg: 'Tạo ảnh anime cô gái gothic lolita váy đen ren dày, băng đô đen, đứng trong vườn hoa tối' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái knight nữ giáp bạc', msg: 'Tạo ảnh anime nữ hiệp sĩ giáp bạc sáng bóng, áo cape đỏ, kiếm dài, tư thế hùng mạnh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái ninja kunoichi', msg: 'Tạo ảnh anime kunoichi ninja, áo đen ôm sát, khăn che mặt, shuriken trên tay, tư thế nhanh nhẹn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái maid cafe', msg: 'Tạo ảnh anime maid girl, đồng phục hầu gái trắng đen, tạp dề ren, tư thế chào đón dễ thương' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái thủy thủ senshi', msg: 'Tạo ảnh anime magical girl thủy thủ, váy biến hình xanh, nơ lớn, tư thế chiến đấu oai phong' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái trang phục Halloween', msg: 'Tạo ảnh anime cô gái hóa trang Halloween: váy phù thủy đen, mũ nhọn, ánh bí ngô cam' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái áo hoodie oversized', msg: 'Tạo ảnh anime cô gái mặc hoodie oversized pastel, quần short, biểu cảm mơ ngủ cute' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái trang phục idol stage', msg: 'Tạo ảnh anime idol girl trên sân khấu, trang phục lấp lánh hồng trắng, confetti bay, lights' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái đồng phục hải quân', msg: 'Tạo ảnh anime cô gái đồng phục hải quân xanh trắng, tóc ngắn, đứng trên boong tàu, gió thổi' },

                // ── Tạo ảnh — Biểu Cảm & Tâm Trạng ────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái cười lấp lánh vui', msg: 'Tạo ảnh anime cô gái cười tươi hết cỡ, mắt cong lên như vầng trăng, má ửng hồng, nền pastel' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái ngẩn người ngạc nhiên', msg: 'Tạo ảnh anime cô gái biểu cảm shock ngạc nhiên, miệng há nhỏ, mắt to tròn, dấu chấm than' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái trầm tư nhìn ra cửa sổ', msg: 'Tạo ảnh anime cô gái ngồi trầm tư nhìn ra cửa sổ mưa, ánh đèn vàng mờ, tâm trạng buồn nhẹ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tức giận chibi', msg: 'Tạo ảnh chibi anime cô gái tức giận, má phồng đỏ, tay nắm đấm, steam trên đầu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái xấu hổ đỏ mặt', msg: 'Tạo ảnh anime cô gái đỏ mặt xấu hổ, tay che mặt, mắt liếc ngang, cute' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái mơ ngủ yên bình', msg: 'Tạo ảnh anime cô gái ngủ yên bình trên chiếc giường trắng, ánh sáng buổi sáng nhẹ nhàng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái tập trung nghiêm túc', msg: 'Tạo ảnh anime cô gái biểu cảm tập trung sắc bén, ánh mắt sắc lạnh, chiến đấu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái mỉm cười khẽ bí ẩn', msg: 'Tạo ảnh anime cô gái mỉm cười nhẹ bí ẩn, ánh mắt sâu thẳm, nền tối gradient' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái hét vui khi thắng', msg: 'Tạo ảnh anime cô gái hét vui mừng, tay đấm lên trời, confetti xung quanh, nền sáng rực' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái khóc ôm gối', msg: 'Tạo ảnh anime cô gái ôm gối nhỏ khóc thút thít, tóc xõa, ánh đèn đêm vàng mờ' },

                // ── Tạo ảnh — Cảnh Chiến Đấu Anime ─────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Nữ kiếm sĩ tấn công', msg: 'Tạo ảnh anime nữ kiếm sĩ tấn công với kiếm phát sáng, hiệu ứng tốc độ, kẻ thù mờ phía sau' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Nhân vật dùng phép lửa', msg: 'Tạo ảnh anime nhân vật nữ bùng phát lửa đỏ cam xung quanh, mắt phát sáng, tư thế uy mãnh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái xạ thủ bắn tên', msg: 'Tạo ảnh anime cô gái xạ thủ giương cung sáng, ánh mắt tập trung, tên phát sáng, rừng tối' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Nữ pháp sư triệu hồi', msg: 'Tạo ảnh anime nữ pháp sư đứng giữa vòng phép thuật, rồng nhỏ được triệu hồi, ánh tím huyền bí' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái sniper tầm xa', msg: 'Tạo ảnh anime cô gái sniper nằm bắn tầm xa, scope cận cảnh mắt, nền thành phố phía sau' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Chiến binh anime dual wield', msg: 'Tạo ảnh anime nữ chiến binh cầm 2 kiếm ngắn, tóc ngắn bừa bộn, máu bắn nhẹ, dramatic lighting' },

                // ── Tạo ảnh — Thời Tiết & Mùa ──────────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái dưới mưa lớn', msg: 'Tạo ảnh anime cô gái đứng giữa cơn mưa to, không ô, áo ướt sũng, biểu cảm thản nhiên' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Mùa hạ hoa hướng dương', msg: 'Tạo ảnh anime cô gái đứng giữa cánh đồng hướng dương mùa hè rực rỡ, nón cói, váy vàng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái trong cơn bão tuyết', msg: 'Tạo ảnh anime cô gái đi trong bão tuyết, áo choàng ôm chặt, tóc bay mạnh, cô đơn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Mùa thu lá đỏ Nhật Bản', msg: 'Tạo ảnh anime cô gái ngồi trên bậc đá dưới cây phong đỏ rực, lá rơi, yên bình' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái lúc rạng đông', msg: 'Tạo ảnh anime cô gái đứng trên đỉnh đồi ngắm bình minh, ánh sáng vàng hồng đầu tiên' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Mưa đêm thành phố anime', msg: 'Tạo ảnh anime góc phố đêm mưa nhỏ, đèn đường vàng, bóng người đi bộ từ xa, phong cảnh buồn đẹp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái nhảy trong tuyết', msg: 'Tạo ảnh anime cô gái nhảy vui vẻ trong tuyết rơi, áo choàng đỏ, xung quanh đầy tuyết trắng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái ngắm sao đêm', msg: 'Tạo ảnh anime cô gái nằm trên thảo nguyên ngắm bầu trời đầy sao, dải Ngân Hà rực rỡ' },

                // ── Tạo ảnh — Anime Chibi & Cute ────────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Chibi party nhỏ', msg: 'Tạo ảnh chibi anime nhiều nhân vật nhỏ dễ thương cùng tiệc sinh nhật, bánh kem, confetti' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Chibi ngủ với thú bông', msg: 'Tạo ảnh chibi anime cô gái nhỏ ngủ ôm gấu bông to, nền xanh sao, dễ thương tuyệt đối' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Chibi cặp đôi bạn thân', msg: 'Tạo ảnh 2 chibi anime bạn thân ngồi cạnh nhau ăn kem, biểu cảm vui, màu pastel mềm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Chibi thám hiểm nhỏ', msg: 'Tạo ảnh chibi anime cô gái nhỏ mặc đồ thám hiểm, mũ cứng, kính lúp, đứng trước hang tối vui vẻ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Chibi magical transformation', msg: 'Tạo ảnh chibi anime biến hình thành magical girl, sáng chói, váy xoay tròn, sparkle' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Chibi Halloween cute', msg: 'Tạo ảnh chibi anime Halloween dễ thương, hóa trang ma nhỏ, bí ngô, màu cam đen pastel' },

                // ── Tạo ảnh — Bối Cảnh Sci-fi & Tương Lai ──────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái android cyborg', msg: 'Tạo ảnh anime cô gái android cyborg, nửa người nửa máy, mắt phát sáng xanh, nền lab tối' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Phi công vũ trụ nữ', msg: 'Tạo ảnh anime nữ phi công vũ trụ trong cockpit, nền sao vũ trụ xanh, biểu cảm quyết đoán' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái thành phố nổi tương lai', msg: 'Tạo ảnh anime cô gái đứng ban công nhìn ra thành phố tương lai nổi, drone bay, ánh đèn rực rỡ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái mặc suit sci-fi', msg: 'Tạo ảnh anime cô gái mặc bộ suit chiến đấu sci-fi ôm sát phát sáng, đứng trên planet lạ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime mech pilot nữ', msg: 'Tạo ảnh anime nữ pilot bước ra từ cockpit mech robot khổng lồ, tóc bừa bộn cool ngầu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Hologram anime girl', msg: 'Tạo ảnh anime cô gái hologram kỹ thuật số, semi-transparent, glitch effect nhẹ, màu tím xanh cyan' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái chạy qua portal', msg: 'Tạo ảnh anime cô gái nhảy qua cổng portal phát sáng tím xanh, motion blur nhanh' },

                // ── Tạo ảnh — Phong Cách Vẽ Đặc Biệt ───────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Phong cách Makoto Shinkai', msg: 'Tạo ảnh anime phong cảnh cô gái nhìn ra cửa sổ mưa, ánh sáng đẹp như phim Your Name' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Phong cách Studio Ghibli', msg: 'Tạo ảnh phong cách Ghibli cánh đồng cỏ xanh, cô gái nhỏ, bầu trời mây xanh, yên bình như Spirited Away' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Phong cách Kyoto Animation', msg: 'Tạo ảnh anime phong cách KyoAni, cô gái cute, chi tiết cao, lighting đẹp, cảnh trường học' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime oil painting style', msg: 'Tạo ảnh anime phong cách oil painting, nét vẽ rộng, màu sắc đậm đà, cảnh thiên nhiên' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Watercolor anime soft', msg: 'Tạo ảnh anime phong cách màu nước mềm mại, nét nhòe nhẹ, màu pastel tinh tế, dreamy' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime sketch pencil art', msg: 'Tạo ảnh anime phong cách phác thảo chì, nét vẽ tay tự nhiên, chiaroscuro đẹp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Pixel art anime retro', msg: 'Tạo ảnh pixel art anime retro 16-bit, nhân vật cute, bảng màu giới hạn, phong cách game cổ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime neon noir dark', msg: 'Tạo ảnh anime neon noir tối: nền đen, outline neon đỏ xanh, phong cách Sin City anime' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime flat color minimal', msg: 'Tạo ảnh anime phong cách flat color tối giản, bóng đổ đơn giản, màu sắc sáng rõ ràng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime ink brush sumi-e', msg: 'Tạo ảnh kết hợp anime và tranh mực tàu sumi-e: cô gái, cây trúc, bố cục tối giản đẹp' },

                // ── Tạo ảnh — Cặp Đôi & Tình Huống Lãng Mạn ────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Cặp đôi anime dưới hoa anh đào', msg: 'Tạo ảnh anime cặp đôi đứng dưới mưa hoa anh đào, nhìn nhau, ánh chiều vàng ấm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cặp đôi anime ở quán cà phê', msg: 'Tạo ảnh anime hai người ngồi đối diện trong quán café ấm áp, tay chạm nhẹ, ánh chiều' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime slow dance đêm mưa', msg: 'Tạo ảnh anime cặp đôi khiêu vũ chậm dưới mưa đêm, ánh đèn đường, lãng mạn buồn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Bạn bè anime picnic mùa hè', msg: 'Tạo ảnh anime nhóm bạn picnic bãi cỏ mùa hè, bánh sandwich, trải khăn ca-rô, vui vẻ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái cùng thú cưng rồng nhỏ', msg: 'Tạo ảnh anime cô gái ngủ trưa, rồng con nhỏ ngồi trên ngực, ánh nắng dịu, ấm áp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái và chó shiba', msg: 'Tạo ảnh anime cô gái ngồi ôm shiba inu to, công viên mùa thu, cả hai vui vẻ hạnh phúc' },

                // ── Tạo ảnh — Illustrious & NoobAI Style ────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Illustrious XL — cô gái detail cao', msg: 'Tạo ảnh anime Illustrious XL cô gái tóc bạch kim dài, mắt xanh to, chi tiết cực cao, ánh studio' },
                { icon: 'image', label: 'Tạo ảnh', text: 'NoobAI — close-up khuôn mặt', msg: 'Tạo ảnh anime NoobAI close-up khuôn mặt cô gái, da mịn màng, lông mi dày, ánh mắt sâu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Illustrious — half body portrait', msg: 'Tạo ảnh anime half-body portrait cô gái kimono hiện đại, ánh sáng soft dramatic' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime full body dynamic pose', msg: 'Tạo ảnh anime full body cô gái dynamic action pose, tóc bay, quần áo fluttering, motion' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime back shot bí ẩn', msg: 'Tạo ảnh anime cô gái chụp từ phía sau, nhìn ra cảnh quan hùng vĩ, tóc dài bay gió' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime từ góc thấp worm-eye', msg: 'Tạo ảnh anime nhìn từ dưới lên, cô gái nhìn xuống camera, bầu trời phía sau, góc độ độc đáo' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime bird-eye từ trên cao', msg: 'Tạo ảnh anime góc nhìn từ trên cao, cô gái nhỏ bé giữa cánh đồng hoa khổng lồ' },

                // ── Tạo ảnh — Ý Tưởng Sáng Tạo ─────────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl made of stars', msg: 'Tạo ảnh surreal anime cô gái cơ thể tạo thành từ các ngôi sao và tinh vân, nền không gian' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Reflection world anime', msg: 'Tạo ảnh anime cô gái đứng trước gương nước, phản chiếu thế giới ngược hoàn toàn khác' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl trong bong bóng xà phòng', msg: 'Tạo ảnh anime cô gái ngồi trong bong bóng xà phòng khổng lồ lung linh, bay lên bầu trời' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime 4 mùa split panel', msg: 'Tạo ảnh anime 4 panel chia đôi: cùng cô gái, 4 mùa xuân hạ thu đông, phong cách elegant' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái và con búp bê giống y', msg: 'Tạo ảnh anime cô gái cầm con búp bê trông giống hệt mình, uncanny atmosphere, bí ẩn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl thành tranh vẽ', msg: 'Tạo ảnh meta-anime: cô gái đang được vẽ trong tranh, nửa thật nửa tô màu, sáng tạo' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime world inside teacup', msg: 'Tạo ảnh surreal: thế giới anime thu nhỏ bên trong tách trà, cánh đồng hoa, trời mây nhỏ xíu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái và phiên bản shadow', msg: 'Tạo ảnh anime cô gái và bóng tối phía sau có hình dáng khác hoàn toàn, đối lập' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl đọc sách bay', msg: 'Tạo ảnh anime cô gái đọc sách ngồi không trung, trang sách bay tung tóe xung quanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl thời gian đóng băng', msg: 'Tạo ảnh anime cô gái đứng giữa cảnh thời gian đóng băng: mưa dừng giữa không trung, lá bay chết lặng' },

                // ── Tạo ảnh — Anime & Manga Mix Style ───────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Manga black & white dramatic', msg: 'Tạo ảnh theo phong cách manga đen trắng với hiệu ứng speed lines, nhân vật biểu cảm mạnh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime retro 90s style', msg: 'Tạo ảnh anime phong cách thập niên 90, màu sắc vintage, nét vẽ đặc trưng sailor moon era' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime modern sharp 2024', msg: 'Tạo ảnh anime phong cách hiện đại 2024: nét sắc, màu sắc sáng bão, chi tiết cực cao' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime lofi aesthetic', msg: 'Tạo ảnh anime lofi aesthetic: cô gái học bài đêm khuya, mèo bên cạnh, cốc cà phê, ánh đèn vàng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime vaporwave aesthetic', msg: 'Tạo ảnh anime vaporwave: màu tím hồng cyan pastel, lưới grid, mặt trời ảo, retrowave vibes' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime dark academia', msg: 'Tạo ảnh anime dark academia: thư viện cổ tối, áo blazer, sách, ánh nến, tông màu nâu tối ấm' },

                // ── Tạo ảnh — Wuthering Waves & Blue Archive ────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Rover Wuthering Waves', msg: 'Tạo ảnh anime Rover (Wuthering Waves) tóc đen, áo choàng xám, kiếm, nền thế giới hậu apocalypse' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Jiyan Wuthering Waves', msg: 'Tạo ảnh anime Jiyan (Wuthering Waves) phong cách tướng quân, long spear, áo giáp đỏ xanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Yuuka Blue Archive', msg: 'Tạo ảnh anime Yuuka (Blue Archive) tóc xanh lá, đồng phục học sinh, biểu cảm nghiêm túc dễ thương' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Hoshino Blue Archive', msg: 'Tạo ảnh anime Hoshino (Blue Archive) mắt hồng, tóc trắng, tư thế lười biếng ngủ gật cute' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Umamusume horse girl race', msg: 'Tạo ảnh anime Umamusume horse girl trên đường đua, tai ngựa, tóc bay, tốc độ tối đa, đẹp' },

                // ── Tạo ảnh — Misc Themed ────────────────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái bé bỏng và khổng lồ', msg: 'Tạo ảnh anime size comparison: cô gái chibi nhỏ xíu đứng trên bàn tay người khổng lồ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl với katana', msg: 'Tạo ảnh anime cô gái cầm katana nhìn xuống lưỡi kiếm, ánh hoàng hôn đỏ, tóc ngắn lạnh lùng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime potion maker alchemist', msg: 'Tạo ảnh anime nữ giả kim thuật sĩ đang pha chế thuốc, bình thuốc bong bóng sủi, áo choàng lộn xộn cute' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl café chủ', msg: 'Tạo ảnh anime cô chủ quán café dễ thương, tạp dề, đang pha cà phê latte art, quán ấm áp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl photographer', msg: 'Tạo ảnh anime cô gái chụp ảnh phóng viên, máy ảnh phim cũ, đứng giữa cánh đồng hoa' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl violinist', msg: 'Tạo ảnh anime cô gái chơi đàn violin trên mái nhà, ánh đêm thành phố phía sau, tóc bay gió' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl painter', msg: 'Tạo ảnh anime cô gái họa sĩ trước giá vẽ, quần áo vấy sơn, biểu cảm tập trung đáng yêu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime garden tea party', msg: 'Tạo ảnh anime tiệc trà ngoài vườn, cô gái váy ren trắng, bánh ngọt, ấm trà, hoa nở' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl thiên nga trắng', msg: 'Tạo ảnh anime cô gái mặc váy lông thiên nga trắng đứng giữa hồ, ánh trăng phản chiếu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime demon slayer inspired', msg: 'Tạo ảnh anime phong cách Demon Slayer: nhân vật nữ haori đặc trưng, thanh kiếm, hoa ngục' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái anime thám tử', msg: 'Tạo ảnh anime cô gái thám tử, áo mưa, mũ nồi, kính lúp, phố đêm mưa, bí ẩn kiểu noir' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái anime tiên nữ nước', msg: 'Tạo ảnh anime nàng tiên nữ nước, cánh trong suốt, tóc xanh ngọc, nổi trên mặt hồ, ánh sáng tiên' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl với origami', msg: 'Tạo ảnh anime cô gái xếp origami, những con hạc giấy bay quanh, ánh chiều mềm, Nhật Bản' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime idol concert stage', msg: 'Tạo ảnh anime concert idol lớn, đèn laser, crowd đông, nhân vật chính trên sân khấu rực rỡ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl yoga morning', msg: 'Tạo ảnh anime cô gái yoga buổi sáng sớm, nền biển, ánh hồng bình minh, yên bình' },

                // ── Tạo ảnh — Bầu Không Khí & Ánh Sáng ─────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime volumetric light rừng', msg: 'Tạo ảnh anime ánh sáng volumetric xuyên qua tán rừng, hạt bụi vàng lơ lửng, cô gái đứng giữa' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime rim light dramatic', msg: 'Tạo ảnh anime cô gái được chiếu rim light từ sau, nền tối, silhouette đẹp mắt nổi bật' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime global illumination nội thất', msg: 'Tạo ảnh anime phòng nội thất đẹp, ánh nắng chiều xuyên cửa sổ, cô gái ngồi đọc sách' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime backlit hoàng hôn', msg: 'Tạo ảnh anime cô gái backlit hoàng hôn đỏ cam, silhouette tối, tóc sáng viền ánh vàng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime candlelight dinner', msg: 'Tạo ảnh anime cô gái ngồi ăn tối ánh nến, ánh nến ấm flickering, nền tối lãng mạn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime moonlight silver', msg: 'Tạo ảnh anime cô gái đứng giữa cánh đồng ánh trăng bạc, bóng dài, tóc trắng phát sáng nhẹ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime neon light portrait', msg: 'Tạo ảnh anime cô gái gần neon sign hồng đỏ, ánh neon phản chiếu da, phong cách lo-fi city pop' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime underwater bioluminescence', msg: 'Tạo ảnh anime cô gái bơi dưới biển đêm, sinh vật phát quang sinh học quanh người, xanh lam tím' },

                // ── Tạo ảnh — Nhân Vật Nam Anime ────────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime boy tóc bạch kim cool', msg: 'Tạo ảnh anime chàng trai tóc bạch kim dài, mắt băng xanh, áo trench coat đen, cool ngầu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime boy wizard staff', msg: 'Tạo ảnh anime pháp sư trẻ cầm staff phát sáng, áo choàng lớn, rừng đêm ma thuật' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime shota chibi cute boy', msg: 'Tạo ảnh anime chibi boy dễ thương tóc nâu xoăn, mắt to, biểu cảm vui nhộn, màu pastel' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime ikemen portrait', msg: 'Tạo ảnh anime ikemen đẹp trai, ánh sáng soft, tóc đen mềm, nụ cười nhẹ, phong cách shoujo manga' },

                // ── Tạo ảnh — Động Vật & Isekai ─────────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime dragon companion', msg: 'Tạo ảnh anime rồng nhỏ màu xanh lá làm bạn đồng hành, ngồi trên vai cô gái, nhìn cùng hướng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime spirit fox trắng', msg: 'Tạo ảnh anime con cáo thần trắng tinh khôi đứng trong rừng tre ánh sáng xanh, thần bí' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime mèo khổng lồ bus Ghibli', msg: 'Tạo ảnh phong cách Ghibli con mèo khổng lồ dễ thương trong rừng đêm, trẻ con ngồi trên lưng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime wolf spirit rider', msg: 'Tạo ảnh anime cô gái cưỡi sói thần khổng lồ màu trắng ánh bạc chạy qua cánh đồng đêm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Isekai anime: ngày đầu', msg: 'Tạo ảnh anime nhân vật isekai vừa bước vào thế giới fantasy, cảnh rừng xanh kỳ bí, lạ lẫm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Isekai anime: dungeon boss room', msg: 'Tạo ảnh anime nhân vật đứng trước cánh cửa boss dungeon khổng lồ phát sáng đỏ, căng thẳng' },

                // ── Tạo ảnh — Phong Cách Đặc Thù Stable Diffusion ───────
                { icon: 'image', label: 'Tạo ảnh', text: 'Highly detailed anime face', msg: 'Tạo ảnh anime ultra-detailed cận khuôn mặt cô gái, từng sợi tóc, lông mi, da chi tiết cực cao' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime 8K ultra resolution portrait', msg: 'Tạo ảnh anime portrait cô gái độ phân giải siêu cao, ánh sáng studio, nền trắng sạch' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime soft focus bokeh', msg: 'Tạo ảnh anime cô gái focus sắc, nền bokeh tròn óng ánh, ánh sáng ban mai mềm mại' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime color palette monochrome blue', msg: 'Tạo ảnh anime monochromatic xanh dương, cô gái và cảnh vật đều tone xanh, đẹp mắt thống nhất' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime golden hour cô gái', msg: 'Tạo ảnh anime cô gái trong golden hour hoàn hảo, da tắm ánh vàng, shadow mềm, đẹp tự nhiên' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime high key bright portrait', msg: 'Tạo ảnh anime high key portrait cô gái, nền trắng, ánh sáng đầy, tone sáng rực tươi mới' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime low key dark portrait', msg: 'Tạo ảnh anime low key portrait cô gái, tối phần lớn khung hình, chỉ mặt được chiếu sáng, bí ẩn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime dynamic tilt shift', msg: 'Tạo ảnh anime miniature effect tilt-shift, cảnh thành phố trông như đồ chơi, màu sắc vibrant' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime split complementary colors', msg: 'Tạo ảnh anime sử dụng màu bổ sung: cam xanh dương tím, bố cục cô gái trung tâm, ấn tượng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime wabi-sabi aesthetic', msg: 'Tạo ảnh anime wabi-sabi: ngôi nhà cũ, rêu mọc, nhân vật lớn tuổi, vẻ đẹp không hoàn hảo' },

                // ── Tạo ảnh — Điển Tích & Thần Thoại ───────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Thần thoại Hy Lạp anime', msg: 'Tạo ảnh anime nữ thần Athena: áo giáp vàng, cú mèo, khiên rắn Medusa, nền đền Parthenon' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Thần thoại Norse anime', msg: 'Tạo ảnh anime Valkyrie Norse, áo giáp bạc có cánh, giáo vàng, nền Valhalla' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Thần thoại Nhật Bản anime', msg: 'Tạo ảnh anime nữ thần Amaterasu, áo kimono trắng vàng rực, ánh mặt trời, cáo trắng bên cạnh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Truyền thuyết Việt Nam anime', msg: 'Tạo ảnh anime phong cách Tiên Dung Chử Đồng Tử: nữ nhân mặc lụa trắng, bên sông, sen nở' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime mermaid nhân ngư', msg: 'Tạo ảnh anime nàng tiên cá tóc đỏ dài, vảy xanh ngọc lấp lánh, ngồi trên đá giữa biển' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime phoenix nữ thần lửa', msg: 'Tạo ảnh anime nữ thần Phụng Hoàng, cánh lửa cam đỏ khổng lồ, bay giữa hoàng hôn cháy rực' },

                // ── Tạo ảnh — Khác Biệt & Thú Vị ───────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime crossover Genshin x HSR', msg: 'Tạo ảnh anime crossover Traveler (Genshin) và Trailblazer (HSR) đứng cạnh nhau, nhìn về một hướng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime múa đầu lân Tết', msg: 'Tạo ảnh anime cô gái tham gia múa đầu lân Tết Nguyên Đán, pháo sáng đỏ, vui tươi' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime cô gái nghịch tuyết', msg: 'Tạo ảnh anime cô gái làm người tuyết, má đỏ vì lạnh, khăn quàng, biểu cảm tập trung cute' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime stargazer observatory', msg: 'Tạo ảnh anime cô gái bên kính thiên văn lớn trong đài quan sát, bầu trời sao qua mái kính' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl gặp chính mình', msg: 'Tạo ảnh anime cô gái gặp bản thân từ timeline song song, hai người ăn mặc khác hoàn toàn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime retro game 8-bit world', msg: 'Tạo ảnh anime cô gái đứng trong thế giới 8-bit, pixel scenery xung quanh, bản thân vẫn full anime' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl pha cocktail bar', msg: 'Tạo ảnh anime cô gái bartender pha cocktail màu sắc, ánh đèn quầy bar ấm, biểu cảm chuyên nghiệp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime graffiti street art', msg: 'Tạo ảnh anime cô gái spray graffiti art trên tường, hoodie, cap ngược, thành phố đêm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl và robot bạn', msg: 'Tạo ảnh anime cô gái ngồi cạnh robot bạn nhỏ cute, chia sẻ ăn kem, công viên, thân thiết' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime sakura matsuri đêm', msg: 'Tạo ảnh anime lễ hội hoa anh đào đêm, đèn lồng đỏ trên đầu, cô gái mặc yukata, sakura trắng hồng rơi' },

                // ── Tạo ảnh — LoRA-specific prompts ─────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Firefly SAM Mecha armor', msg: 'Tạo ảnh Firefly HSR trong bộ mecha SAM, firefly (ar-26710), plugsuit, tư thế chiến đấu oai hùng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Stelle trailblazer casual', msg: 'Tạo ảnh Stelle HSR (st3ll3g1rl) trang phục casual, tóc xám, mắt vàng, biểu cảm tự nhiên vui vẻ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Huohuo áo truyền thống', msg: 'Tạo ảnh Huohuo HSR (huohuodef) đứng trong đền Trung Hoa, đuôi cáo xanh lá, áo truyền thống' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Silver Wolf ngồi game', msg: 'Tạo ảnh Silver Wolf HSR ngồi chơi game handheld, kính mát để lệch, phòng tối ánh màn hình' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Kafka đứng giữa đêm', msg: 'Tạo ảnh Kafka HSR đứng giữa con phố vắng đêm, ánh đèn đường tím, nụ cười bí ẩn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'The Herta ngai vàng', msg: 'Tạo ảnh The Herta ngồi ngai vàng phòng nghiên cứu, con búp bê nhỏ xung quanh, h3rta trigger' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Lynx mùa đông leo núi', msg: 'Tạo ảnh Lynx Landau HSR mặc đồ leo núi mùa đông, tuyết dày, biểu cảm cố gắng cute' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Robin trên sân khấu nhỏ', msg: 'Tạo ảnh Robin HSR hát trên sân khấu nhỏ ấm cúng, cánh trắng thu lại, micro cầm tay, ánh đèn vàng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Hyacine học bài', msg: 'Tạo ảnh Hyacine HSR (hyac1ne) ngồi học bài, sách vở bày ra, drill hair cute, phòng học xinh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cyrene dưới trăng đêm', msg: 'Tạo ảnh Cyrene HSR đứng dưới trăng tròn, hoa cài tóc, áo trắng bồng bềnh, ánh trăng bạc' },

                // ── Tạo ảnh — Hai Nhân Vật & Interaction ────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Firefly x Stelle duo', msg: 'Tạo ảnh anime Firefly và Stelle (HSR) đứng cạnh nhau nhìn về phía trời, nền vũ trụ rực rỡ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Kafka x Silver Wolf', msg: 'Tạo ảnh anime Kafka và Silver Wolf ngồi cạnh nhau trong quán café, cả hai nhìn ra cửa sổ đêm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Huohuo bị chọc ghẹo', msg: 'Tạo ảnh anime Huohuo bị bạn đồng hành chọc ghẹo, mặt đỏ hậm hực, đuôi cáo dựng lên tức giận' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Hai cô gái cầm tay', msg: 'Tạo ảnh anime hai cô gái tóc đối lập sáng tối cầm tay chạy qua cánh đồng, ánh chiều vàng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cô gái và giáo viên phép thuật', msg: 'Tạo ảnh anime học trò và thầy cô giáo phép thuật, học trong thư viện tháp cao, nến lơ lửng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Chiến binh và healer pair', msg: 'Tạo ảnh anime chiến binh nữ bị thương và healer đang chữa trị, ánh sáng xanh chữa lành' },

                // ── Tạo ảnh — Màu Sắc Chủ Đạo ──────────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Tone đỏ — fire & passion', msg: 'Tạo ảnh anime toàn tone đỏ: cô gái tóc đỏ, lửa quanh người, nền đỏ thẫm, passion' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Tone xanh lá — forest spirit', msg: 'Tạo ảnh anime toàn tone xanh lá: spirit rừng cô gái, nền rừng già, ánh sáng xanh bóng bẩy' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Tone tím — mystery & magic', msg: 'Tạo ảnh anime toàn tone tím: phù thủy nữ, tinh thể tím, nền tím huyền bí, magical' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Tone vàng — golden goddess', msg: 'Tạo ảnh anime toàn tone vàng: nữ thần mặc vàng, ánh sáng vàng rực, tóc vàng, hào quang' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Tone trắng — purity & ice', msg: 'Tạo ảnh anime toàn tone trắng: cô gái tóc trắng, tuyết trắng, áo trắng, tinh khiết thanh cao' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Tone đen — shadow & elegance', msg: 'Tạo ảnh anime toàn tone đen: gothic cô gái đen, bóng tối, chỉ highlight trắng viền nổi bật' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Pastel rainbow — candy world', msg: 'Tạo ảnh anime thế giới candy pastel rainbow, tất cả màu sắc nhẹ nhàng, cô gái cute trung tâm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Cyan magenta duotone', msg: 'Tạo ảnh anime duotone cyan và magenta, cô gái silhouette, đường phố đêm, phong cách cyberpunk' },

                // ── Tạo ảnh — Cận Cảnh & Macro ──────────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Closeup đôi mắt anime', msg: 'Tạo ảnh anime extreme close-up đôi mắt, iris chi tiết, phản chiếu cảnh quan bên trong, beautiful' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Closeup đôi môi anime', msg: 'Tạo ảnh anime close-up đôi môi hồng mềm, ánh gloss nhẹ, hơi hé mở, aesthetic' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Closeup bàn tay cầm hoa', msg: 'Tạo ảnh anime cận cảnh bàn tay cô gái cầm bông hoa, ngón tay thon, ánh sáng mềm' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Closeup tai với khuyên', msg: 'Tạo ảnh anime close-up tai cô gái với khuyên tai tinh xảo, tóc hé một bên, ánh sáng nhẹ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Silhouette anime dramatic', msg: 'Tạo ảnh anime silhouette cô gái tối đen trên nền gradient mặt trời lặn đỏ cam đẹp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime reflection in eyes', msg: 'Tạo ảnh anime khuôn mặt cô gái, trong mắt phản chiếu cảnh thành phố hay bầu trời sao' },

                // ── Tạo ảnh — Experimental & Abstract ───────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime glitch digital error', msg: 'Tạo ảnh anime cô gái với hiệu ứng glitch kỹ thuật số: pixel vỡ, màu RGB shift, bí ẩn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime dissolve into particles', msg: 'Tạo ảnh anime cô gái đang tan thành các hạt particle nhỏ bay đi, hiệu ứng đẹp mắt' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime double exposure', msg: 'Tạo ảnh anime double exposure: khuôn mặt cô gái chồng lên cảnh rừng hay thành phố' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime ink drop spreading', msg: 'Tạo ảnh anime cô gái xuất hiện từ mực loang trong nước, nét vẽ hòa tan, đẹp nghệ thuật' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime origami paper world', msg: 'Tạo ảnh anime thế giới tạo từ giấy origami, cô gái origami paper art, gấp nếp rõ ràng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime stained glass window', msg: 'Tạo ảnh anime cô gái được tái hiện như kính màu stained glass nhà thờ, màu sắc rực rỡ ánh sáng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime lego brick style', msg: 'Tạo ảnh anime nhân vật xây từ lego brick nhỏ, cute và quirky, màu sắc tươi sáng' },

                // ── Tạo ảnh — Thêm Cảnh Quan ────────────────────────────
                { icon: 'image', label: 'Tạo ảnh', text: 'Tháp Eiffel anime đêm', msg: 'Tạo ảnh anime Tháp Eiffel Paris đêm lấp lánh, cô gái người Việt đứng ngắm, lãng mạn' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Núi Phú Sĩ anime', msg: 'Tạo ảnh anime núi Phú Sĩ mùa xuân hoa anh đào, hồ Kawaguchiko phản chiếu, trời xanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Đại lộ Champs-Élysées anime', msg: 'Tạo ảnh anime đại lộ Champs-Élysées thu với lá vàng rụng, ánh chiều vàng đẹp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Hồ Hoàn Kiếm anime', msg: 'Tạo ảnh anime phong cách Hồ Hoàn Kiếm Hà Nội, Tháp Rùa, mùa thu lá vàng, cô gái áo dài' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Hang Sơn Đoòng fantasy', msg: 'Tạo ảnh anime phong cách hang Sơn Đoòng Quảng Bình tuyệt đẹp, ánh sáng kỳ diệu bên trong' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Biển đảo Phú Quốc anime', msg: 'Tạo ảnh anime bãi biển Phú Quốc xanh ngọc, nước trong vắt, cô gái ngồi trên đá san hô' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Ruộng bậc thang Mù Cang Chải', msg: 'Tạo ảnh anime ruộng bậc thang mùa lúa chín vàng, cô gái dân tộc Mông, mây núi hùng vĩ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl với bộ thẻ tarot', msg: 'Tạo ảnh anime cô gái bí ẩn giữa những lá bài tarot bay quanh, ánh nến, bóng tối huyền bí' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl ngủ trong kén hoa', msg: 'Tạo ảnh anime cô gái ngủ trong kén hoa khổng lồ, cánh hoa ôm quanh, ánh sáng xanh lam dịu' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime chibi bộ tứ team', msg: 'Tạo ảnh 4 chibi anime team, mỗi người một màu chủ đạo khác nhau, cùng tư thế đoàn kết' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl đọc thư dưới cây', msg: 'Tạo ảnh anime cô gái ngồi dựa gốc cây to, đọc lá thư, ánh chiều lọc qua tán lá xanh' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl thiết kế thời trang', msg: 'Tạo ảnh anime cô gái thiết kế thời trang, bên giá vẽ đầy phác thảo váy áo, kéo, kim chỉ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime phòng ngủ cozy night', msg: 'Tạo ảnh anime phòng ngủ cozy ban đêm, đèn fairy lights trên tường, chăn bông dễ thương, ấm áp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl tắm ánh sao băng', msg: 'Tạo ảnh anime cô gái giơ tay đón sao băng, đứng trên mái nhà đêm, mưa sao băng đẹp' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime autumn girl red maple', msg: 'Tạo ảnh anime cô gái đứng giữa rừng phong đỏ rực mùa thu, lá đỏ rơi đầy không trung' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl trên đu quay carnival', msg: 'Tạo ảnh anime cô gái ngồi trên đu quay hội chợ ban đêm, đèn màu quanh, biểu cảm thích thú' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Anime girl bầu trời tím hoàng hôn', msg: 'Tạo ảnh anime cô gái đứng đồng trống, bầu trời hoàng hôn tím hồng đẹp, một mình yên lặng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Harness lingerie neon night', msg: 'Tạo ảnh anime cô gái mặc lingerie02 harness, skindentation, đứng giữa phố đêm neon cyberpunk, ánh đèn tím hồng bao quanh, phong cách sexy noir' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Kanon leotard moonlight', msg: 'Tạo ảnh anime cô gái mặc lingerie01 leotard frills, fishnet thighhighs, elbow gloves, đứng dưới ánh trăng phản chiếu lên người, nền tối sang trọng' },
                { icon: 'image', label: 'Tạo ảnh', text: 'See-through babydoll rain', msg: 'Tạo ảnh anime cô gái mặc lingerie see-through babydoll frills animal print, đứng trong mưa nhẹ, ướt nhẹ, ánh sáng buổi chiều mờ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Transparent lingerie vanity mirror', msg: 'Tạo ảnh anime cô gái mặc sexy lingerie translucent transparent đứng trước gương trang điểm, ánh đèn vàng ấm, biểu cảm tự tin quyến rũ' },
                { icon: 'image', label: 'Tạo ảnh', text: 'Christmas detective lingerie', msg: 'Tạo ảnh anime cô gái mặc lingerie03 blue bikini fur trim, blue thighhighs, heart o-ring, cape phất phới trong tuyết Giáng sinh, pose tự tin' },

                // ── Tư vấn / Tips ──────────────────────────────────────
                { icon: 'trending-up', label: 'Tư vấn', text: '5 tips tăng năng suất', msg: 'Cho tôi 5 tips tăng năng suất làm việc hiệu quả' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Lộ trình học lập trình', msg: 'Tư vấn lộ trình học lập trình từ zero cho người mới bắt đầu' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Học tiếng Anh 6 tháng', msg: 'Tư vấn cách học tiếng Anh hiệu quả trong 6 tháng' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Quản lý thời gian', msg: 'Gợi ý các phương pháp quản lý thời gian hiệu quả như Pomodoro, GTD' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Cách học một kỹ năng mới', msg: 'Phương pháp học một kỹ năng mới nhanh nhất trong 30 ngày' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Xây dựng thói quen tốt', msg: 'Cách xây dựng thói quen tốt và duy trì lâu dài theo khoa học' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Tư duy tài chính cơ bản', msg: 'Các nguyên tắc tài chính cá nhân cơ bản cho người trẻ' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Chuẩn bị phỏng vấn kỹ thuật', msg: 'Hướng dẫn chuẩn bị phỏng vấn kỹ thuật cho vị trí developer' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Làm thế nào để nghỉ ngơi hiệu quả?', msg: 'Cách nghỉ ngơi và phục hồi năng lượng hiệu quả sau ngày dài làm việc' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Overcome procrastination', msg: 'Các kỹ thuật thực tế để vượt qua tình trạng trì hoãn công việc' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Học toán cho lập trình', msg: 'Các mảng toán học quan trọng cần biết để học Machine Learning' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Tự học Data Science', msg: 'Lộ trình tự học Data Science trong 6 tháng với tài nguyên miễn phí' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Cân bằng công việc và cuộc sống', msg: 'Cách cân bằng giữa công việc và cuộc sống cá nhân khi làm remote' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Portfolio developer', msg: 'Cách xây dựng portfolio developer ấn tượng khi chưa có kinh nghiệm' },
                { icon: 'trending-up', label: 'Tư vấn', text: 'Đọc sách hiệu quả', msg: 'Kỹ thuật đọc sách nhanh và ghi nhớ tốt hơn' },

                // ── Sáng tạo / Viết lách ──────────────────────────────
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Truyện ngắn du hành thời gian', msg: 'Viết một truyện ngắn về cô gái nhặt được chiếc đồng hồ du hành thời gian' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Thơ về Hà Nội mùa thu', msg: 'Viết một bài thơ ngắn về Hà Nội vào mùa thu lá vàng' },
                { icon: 'pen-line', label: 'Sáng tạo', text: '5 ý tưởng startup AI', msg: 'Cho tôi 5 ý tưởng startup sáng tạo trong lĩnh vực AI và EdTech' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Email marketing hấp dẫn', msg: 'Viết email marketing cho sản phẩm ứng dụng productivity' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Kịch bản phim ngắn', msg: 'Viết kịch bản phim ngắn 5 phút về tình bạn giữa người và robot' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Slogan cho thương hiệu', msg: 'Tạo 10 slogan sáng tạo cho thương hiệu cà phê Việt Nam' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Bài rap về lập trình', msg: 'Viết một đoạn rap vui về cuộc sống của lập trình viên' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Truyện kinh dị ngắn', msg: 'Viết một truyện kinh dị ngắn, không gian 1 phòng, không có yếu tố siêu nhiên' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Thư gửi bản thân tương lai', msg: 'Viết một bức thư gửi cho bản thân mình 10 năm sau' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Mô tả nhân vật game', msg: 'Viết mô tả chi tiết cho nhân vật boss trong game nhập vai fantasy' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Caption Instagram hay', msg: 'Viết 5 caption Instagram sáng tạo cho ảnh du lịch biển' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Bài hát về mùa hè', msg: 'Viết lời bài hát về mùa hè ở Đà Nẵng, phong cách indie' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Ý tưởng trò chơi nhập vai', msg: 'Brainstorm ý tưởng cho một trò chơi nhập vai indie 2D phong cách pixel art' },
                { icon: 'pen-line', label: 'Sáng tạo', text: 'Kịch bản podcast', msg: 'Viết kịch bản tập podcast 10 phút về chủ đề sức khỏe tâm thần' },

                // ── Phân tích / So sánh ──────────────────────────────
                { icon: 'bar-chart-2', label: 'Phân tích', text: 'Remote vs văn phòng', msg: 'Phân tích ưu và nhược điểm của làm việc remote so với văn phòng' },
                { icon: 'bar-chart-2', label: 'Phân tích', text: 'Python vs JavaScript', msg: 'So sánh Python và JavaScript: nên học cái nào trước?' },
                { icon: 'bar-chart-2', label: 'Phân tích', text: 'React vs Vue vs Angular', msg: 'So sánh React, Vue và Angular: framework nào phù hợp cho dự án nhỏ?' },
                { icon: 'bar-chart-2', label: 'Phân tích', text: 'SQL vs NoSQL', msg: 'Khi nào dùng SQL, khi nào dùng NoSQL? So sánh thực tế' },
                { icon: 'bar-chart-2', label: 'Phân tích', text: 'GPT-4o vs Claude vs Gemini', msg: 'So sánh GPT-4o, Claude 3 và Gemini về khả năng và ứng dụng thực tế' },
                { icon: 'bar-chart-2', label: 'Phân tích', text: 'Freelance vs đi làm công ty', msg: 'Phân tích freelance so với làm việc tại công ty cho developer' },
                { icon: 'bar-chart-2', label: 'Phân tích', text: 'Học ĐH vs tự học IT', msg: 'So sánh học đại học IT và tự học để đi làm lập trình' },
                { icon: 'bar-chart-2', label: 'Phân tích', text: 'MacOS vs Windows cho dev', msg: 'MacOS hay Windows tốt hơn cho lập trình viên? Phân tích thực tế' },
                { icon: 'bar-chart-2', label: 'Phân tích', text: 'Startup vs big tech', msg: 'Nên làm ở startup hay big tech? Phân tích cho developer mới ra trường' },
                { icon: 'bar-chart-2', label: 'Phân tích', text: 'Backend vs Frontend vs Full-stack', msg: 'So sánh Backend, Frontend và Full-stack developer: nên theo hướng nào?' },

                // ── Tìm kiếm / Xu hướng ──────────────────────────────
                { icon: 'search', label: 'Tìm kiếm', text: 'Xu hướng AI 2025', msg: 'Tóm tắt các xu hướng AI nổi bật nhất trong năm 2025' },
                { icon: 'search', label: 'Tìm kiếm', text: 'Công nghệ hot nhất 2025', msg: 'Các công nghệ lập trình hot nhất cần học trong 2025' },
                { icon: 'search', label: 'Tìm kiếm', text: 'Jobs AI tốt nhất', msg: 'Các vị trí công việc liên quan đến AI đang có nhu cầu cao nhất' },
                { icon: 'search', label: 'Tìm kiếm', text: 'Framework mới nhất 2025', msg: 'Các framework và thư viện web mới đáng chú ý nhất trong 2025' },
                { icon: 'search', label: 'Tìm kiếm', text: 'Sự kiện tech nổi bật', msg: 'Tóm tắt các sự kiện công nghệ nổi bật nhất gần đây' },
                { icon: 'search', label: 'Tìm kiếm', text: 'Open source hot nhất', msg: 'Các dự án open source nổi bật nhất trên GitHub hiện tại' },
                { icon: 'search', label: 'Tìm kiếm', text: 'Học AI ở đâu miễn phí?', msg: 'Các khóa học AI và Machine Learning miễn phí tốt nhất hiện nay' },

                // ── Hỏi đáp thực tế ─────────────────────────────────
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'Cách fix lỗi pip install', msg: 'Các lỗi thường gặp khi dùng pip install Python và cách fix' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'Git rebase vs merge khác gì?', msg: 'Giải thích sự khác nhau giữa git rebase và git merge, khi nào dùng cái nào' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'Cách tối ưu RAM máy tính', msg: 'Cách tối ưu RAM và tăng tốc máy tính Windows hiệu quả' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'Cách học Git nhanh', msg: 'Hướng dẫn học Git từ đầu cho người mới, các lệnh quan trọng nhất' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'SSH là gì?', msg: 'Giải thích SSH, cách tạo key và dùng SSH để kết nối server' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'API key bảo mật thế nào?', msg: 'Cách bảo mật API key đúng cách, không để lộ trên code' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'Học toán cho AI cần gì?', msg: 'Các kiến thức toán học cần thiết để học AI và Machine Learning' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'Hosting web miễn phí?', msg: 'Các dịch vụ hosting web miễn phí tốt nhất cho project cá nhân' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'Cài Python trên Windows', msg: 'Hướng dẫn cài Python, pip và virtual environment trên Windows' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'VS Code extension tốt nhất', msg: 'Top 10 VS Code extensions hữu ích nhất cho lập trình viên' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'CI/CD là gì?', msg: 'Giải thích CI/CD pipeline và cách setup GitHub Actions cho dự án' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'Cách viết commit tốt', msg: 'Quy ước viết git commit message chuẩn, rõ ràng và chuyên nghiệp' },
                { icon: 'help-circle', label: 'Hỏi đáp', text: 'TypeScript có cần học không?', msg: 'Tại sao nên học TypeScript thay vì JavaScript thuần? Lợi ích thực tế' },

                // ── Cuộc sống / Lifestyle ────────────────────────────
                { icon: 'coffee', label: 'Lifestyle', text: 'Ăn gì tốt cho não?', msg: 'Các loại thực phẩm tốt nhất cho não bộ và trí nhớ' },
                { icon: 'coffee', label: 'Lifestyle', text: 'Tập thể dục không cần gym', msg: 'Bài tập thể dục hiệu quả tại nhà không cần dụng cụ' },
                { icon: 'coffee', label: 'Lifestyle', text: 'Ngủ ít mà không mệt', msg: 'Cách tối ưu giấc ngủ để ngủ ít nhưng vẫn đủ năng lượng' },
                { icon: 'coffee', label: 'Lifestyle', text: 'Giảm căng thẳng hiệu quả', msg: 'Kỹ thuật giảm stress và lo âu hiệu quả được khoa học chứng minh' },
                { icon: 'coffee', label: 'Lifestyle', text: 'Thói quen buổi sáng', msg: 'Morning routine hiệu quả cho người muốn tăng năng suất cả ngày' },
                { icon: 'coffee', label: 'Lifestyle', text: 'Tập trung khi làm việc', msg: 'Cách tập trung sâu và tránh bị phân tâm khi làm việc tại nhà' },
                { icon: 'coffee', label: 'Lifestyle', text: 'Mắt khỏe khi nhìn màn hình', msg: 'Cách bảo vệ mắt khi phải nhìn màn hình máy tính nhiều giờ mỗi ngày' },
                { icon: 'coffee', label: 'Lifestyle', text: 'Ghi chú hiệu quả', msg: 'Phương pháp ghi chú hiệu quả nhất khi học hoặc làm việc' },

                // ── Vui / Thú vị ─────────────────────────────────────
                { icon: 'sparkles', label: 'Thú vị', text: 'Sự kiện kỳ lạ trong lịch sử', msg: 'Kể cho tôi nghe 3 sự kiện kỳ lạ nhất trong lịch sử loài người' },
                { icon: 'sparkles', label: 'Thú vị', text: 'Bí mật của vũ trụ', msg: 'Những bí ẩn lớn nhất của vũ trụ mà khoa học chưa giải thích được' },
                { icon: 'sparkles', label: 'Thú vị', text: 'Sinh vật kỳ lạ nhất', msg: 'Những sinh vật kỳ lạ và độc đáo nhất trên Trái Đất' },
                { icon: 'sparkles', label: 'Thú vị', text: 'Công nghệ tương lai 2050', msg: 'Dự đoán công nghệ nào sẽ thay đổi thế giới vào năm 2050' },
                { icon: 'sparkles', label: 'Thú vị', text: 'Easter eggs trong phần mềm', msg: 'Những easter egg thú vị nổi tiếng nhất được giấu trong phần mềm và game' },
                { icon: 'sparkles', label: 'Thú vị', text: 'Nghịch lý thú vị', msg: 'Giải thích một số nghịch lý nổi tiếng trong triết học và toán học' },
                { icon: 'sparkles', label: 'Thú vị', text: 'Ngôn ngữ lập trình kỳ lạ', msg: 'Các ngôn ngữ lập trình kỳ lạ và thú vị nhất từng được tạo ra' },
                { icon: 'sparkles', label: 'Thú vị', text: 'Sự thật thú vị về não người', msg: '5 sự thật thú vị và ít người biết về não người' },
                { icon: 'sparkles', label: 'Thú vị', text: 'Dự án công nghệ thất bại', msg: 'Những dự án công nghệ từng rất hứa hẹn nhưng cuối cùng thất bại' },
            ];

            function shuffle(arr) {
                for (let i = arr.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [arr[i], arr[j]] = [arr[j], arr[i]];
                }
                return arr;
            }

            const container = document.getElementById('welcomeSuggestions');
            if (!container) return;

            const picked = shuffle([...POOL]).slice(0, 4);
            container.innerHTML = picked.map(s => `
                <button class="welcome__suggestion" data-message="${s.msg.replace(/"/g, '&quot;')}">
                    <div class="welcome__suggestion-title"><i data-lucide="${s.icon}" class="lucide lucide-sm"></i> ${s.label}</div>
                    ${s.text}
                </button>
            `).join('');

            if (window.lucide) lucide.createIcons();

            container.querySelectorAll('.welcome__suggestion').forEach(s => {
                s.addEventListener('click', () => {
                    const msg = s.dataset.message;
                    const input = document.getElementById('messageInput');
                    if (input && msg) {
                        input.value = msg;
                        input.focus();
                        input.dispatchEvent(new Event('input'));
                    }
                });
            });
        })();

});
