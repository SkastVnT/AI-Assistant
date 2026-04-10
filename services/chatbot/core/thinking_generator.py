"""
Thinking Generator - Generates live reasoning/thinking steps for AI responses.

Supports:
1. Real AI reasoning via <think>...</think> tags parsed from model output
2. Native reasoning_content from models like DeepSeek R1 (via REASONING_PREFIX)
3. Fallback template steps for models without reasoning capability
"""
import re
import logging
from typing import Generator, List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Special prefix for reasoning content from models (Grok, DeepSeek R1, etc.)
REASONING_PREFIX = '\x02REASON\x03'


class ThinkTagParser:
    """
    Streaming parser for <think>...</think> tags in AI output.
    
    Feeds chunks of text and yields (is_thinking, text) tuples.
    Handles tags split across multiple chunks via buffering.
    """
    
    # Max length of partial tag we need to buffer
    _MAX_TAG_LEN = len('</think>')  # 8 chars
    
    def __init__(self):
        self.buffer = ''
        self.in_think = False
    
    def feed(self, chunk: str) -> List[Tuple[bool, str]]:
        """
        Feed a streaming chunk. Returns list of (is_thinking, text) tuples.
        
        Args:
            chunk: New text from the stream
        Returns:
            List of (is_thinking, text) — is_thinking=True for reasoning content
        """
        self.buffer += chunk
        results = []
        
        while self.buffer:
            if self.in_think:
                # Looking for </think>
                end_idx = self.buffer.find('</think>')
                if end_idx != -1:
                    thinking_text = self.buffer[:end_idx]
                    if thinking_text:
                        results.append((True, thinking_text))
                    self.buffer = self.buffer[end_idx + len('</think>'):]
                    self.in_think = False
                else:
                    # Emit all but potentially partial tag at the end
                    safe_end = max(0, len(self.buffer) - self._MAX_TAG_LEN)
                    if safe_end > 0:
                        results.append((True, self.buffer[:safe_end]))
                        self.buffer = self.buffer[safe_end:]
                    break  # Wait for more data
            else:
                # Looking for <think>
                start_idx = self.buffer.find('<think>')
                if start_idx != -1:
                    prefix = self.buffer[:start_idx]
                    if prefix.strip():
                        results.append((False, prefix))
                    self.buffer = self.buffer[start_idx + len('<think>'):]
                    self.in_think = True
                else:
                    # Emit all but potentially partial tag at the end
                    safe_end = max(0, len(self.buffer) - self._MAX_TAG_LEN)
                    if safe_end > 0:
                        text = self.buffer[:safe_end]
                        if text.strip():
                            results.append((False, text))
                        self.buffer = self.buffer[safe_end:]
                    break  # Wait for more data
        
        return results
    
    def flush(self) -> List[Tuple[bool, str]]:
        """Flush remaining buffer at end of stream."""
        results = []
        if self.buffer.strip():
            results.append((self.in_think, self.buffer))
        self.buffer = ''
        return results


@dataclass
class ThinkingStep:
    """A single thinking step with title and description"""
    title: str
    description: str = ''
    duration_ms: int = 300
    category: str = 'general'

    @property
    def text(self) -> str:
        """Formatted text with title and optional description"""
        if self.description:
            return f'**{self.title}**\n{self.description}'
        return f'**{self.title}**'


# ─── Message Analysis ─────────────────────────────────────────────

def _extract_keywords(message: str) -> List[str]:
    """Extract meaningful keywords/phrases from the message"""
    stop_words = {
        'là', 'và', 'của', 'cho', 'với', 'trong', 'được', 'có', 'không',
        'này', 'đó', 'một', 'các', 'những', 'để', 'từ', 'lại', 'đã',
        'the', 'is', 'are', 'was', 'were', 'a', 'an', 'and', 'or', 'but',
        'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'this', 'that',
        'it', 'i', 'you', 'he', 'she', 'we', 'they', 'my', 'your',
        'can', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
        'tôi', 'bạn', 'mình', 'cậu', 'anh', 'chị', 'em', 'nó', 'họ',
        'hãy', 'xin', 'vui', 'lòng', 'giúp', 'ơi', 'nhé', 'nha', 'ạ',
        'what', 'how', 'why', 'when', 'where', 'who', 'which',
        'gì', 'sao', 'nào', 'đâu', 'bao',
    }
    words = re.findall(r'[\w]+', message.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 1]
    seen = set()
    unique = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique[:8]


def _detect_intent(message: str) -> Tuple[str, str]:
    """Detect the intent/category. Returns (category, intent_description)"""
    msg = message.lower().strip()

    patterns = [
        ('greeting', r'(xin chào|chào|hello|hi |hey|good morning|good evening)',
         'Chào hỏi'),
        ('code', r'(code|function|class|bug|error|debug|implement|refactor|api|'
         r'algorithm|database|sql|html|css|javascript|python|java|deploy|docker|git|'
         r'lập trình|hàm|lỗi|sửa|viết code|triển khai|syntax|compile|runtime)',
         'Lập trình'),
        ('explain', r'(explain|giải thích|tại sao|why|how does|làm sao|như thế nào|cách)',
         'Giải thích'),
        ('analysis', r'(analyze|analysis|compare|evaluate|phân tích|so sánh|đánh giá)',
         'Phân tích'),
        ('creative', r'(write|story|poem|create|design|imagine|compose|draft|'
         r'viết|truyện|thơ|tạo|thiết kế|sáng tạo|soạn|bài viết)',
         'Sáng tạo'),
        ('math', r'(calculate|math|equation|solve|formula|tính|toán|phương trình|giải)',
         'Toán học'),
        ('translate', r'(translate|dịch|translation|bản dịch|chuyển ngữ|sang tiếng)',
         'Dịch thuật'),
        ('summary', r'(summarize|summary|tóm tắt|tổng kết|overview|recap)',
         'Tóm tắt'),
        ('planning', r'(plan|strategy|roadmap|schedule|kế hoạch|chiến lược|lộ trình|quy trình)',
         'Lập kế hoạch'),
        ('research', r'(research|study|paper|science|theory|nghiên cứu|khoa học|lý thuyết)',
         'Nghiên cứu'),
        ('opinion', r'(what do you think|ý kiến|nghĩ gì|đánh giá|recommend|gợi ý|nên)',
         'Đánh giá'),
    ]

    for category, pattern, desc in patterns:
        if re.search(pattern, msg):
            return category, desc

    if re.search(r'[?？]|\b(what|where|when|who|which|gì|đâu|bao giờ|ai|nào)\b', msg):
        return 'question', 'Câu hỏi'

    if len(msg) > 100:
        return 'complex', 'Phức tạp'

    return 'general', 'Xử lý'


def _truncate(text: str, max_len: int = 80) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + '...'


# ─── Thinking Step Generation ─────────────────────────────────────

def generate_thinking_steps(
    message: str,
    language: str = 'vi',
    context: str = 'casual',
    deep_thinking: bool = False,
) -> Generator[ThinkingStep, None, None]:
    """
    Generate structured thinking steps with bold titles + descriptions,
    similar to Gemini/ChatGPT/Grok thinking display.
    """
    vi = language == 'vi'
    category, intent_desc = _detect_intent(message)
    keywords = _extract_keywords(message)
    msg_short = _truncate(message, 80)
    kw_str = ', '.join(f'"{k}"' for k in keywords[:5]) if keywords else f'"{msg_short}"'

    # ═══ Step 1: Understanding the request ═══
    yield ThinkingStep(
        title='Phân tích yêu cầu' if vi else 'Understanding the request',
        description=(
            f'Đã nhận diện đây là yêu cầu thuộc dạng "{intent_desc}". '
            f'Nội dung cốt lõi xoay quanh: {kw_str}.'
        ) if vi else (
            f'Identified this as a "{intent_desc}" request. '
            f'Core content revolves around: {kw_str}.'
        ),
        duration_ms=350, category=category,
    )

    # ═══ Step 2: Category-specific reasoning ═══
    if category == 'greeting':
        yield ThinkingStep(
            title='Chuẩn bị lời chào' if vi else 'Preparing greeting',
            description=(
                'Người dùng đang bắt đầu cuộc trò chuyện. '
                'Cần phản hồi tự nhiên, thân thiện và mở ra cuộc đối thoại.'
            ) if vi else (
                'User is initiating conversation. '
                'Need natural, friendly response that opens up dialogue.'
            ),
            duration_ms=200, category=category,
        )

    elif category == 'code':
        yield ThinkingStep(
            title='Phân tích yêu cầu kỹ thuật' if vi else 'Analyzing technical requirements',
            description=(
                f'Xác định các thành phần kỹ thuật liên quan: {kw_str}. '
                f'Cần xem xét ngữ cảnh, framework đang dùng và mục tiêu cụ thể.'
            ) if vi else (
                f'Identifying technical components: {kw_str}. '
                f'Need to consider context, framework in use, and specific goal.'
            ),
            duration_ms=350, category=category,
        )
        yield ThinkingStep(
            title='Thiết kế giải pháp' if vi else 'Designing solution',
            description=(
                'Xây dựng giải pháp kỹ thuật phù hợp, bao gồm cấu trúc code, '
                'xử lý edge cases, best practices và error handling.'
            ) if vi else (
                'Building appropriate technical solution including code structure, '
                'edge case handling, best practices, and error handling.'
            ),
            duration_ms=400, category=category,
        )

    elif category == 'explain':
        yield ThinkingStep(
            title='Xây dựng lộ trình giải thích' if vi else 'Building explanation roadmap',
            description=(
                f'Chủ đề cần giải thích liên quan đến: {kw_str}. '
                'Cần cấu trúc từ đơn giản đến phức tạp, kèm ví dụ minh họa cụ thể.'
            ) if vi else (
                f'Topic relates to: {kw_str}. '
                'Need to structure from simple to complex, with concrete illustrative examples.'
            ),
            duration_ms=350, category=category,
        )
        yield ThinkingStep(
            title='Tinh chỉnh cách diễn đạt' if vi else 'Refining explanation',
            description=(
                'Đảm bảo giải thích rõ ràng, tránh thuật ngữ khó hiểu không cần thiết, '
                'và cung cấp đủ ngữ cảnh để người đọc dễ nắm bắt.'
            ) if vi else (
                'Ensuring clarity, avoiding unnecessary jargon, '
                'and providing sufficient context for easy comprehension.'
            ),
            duration_ms=300, category=category,
        )

    elif category == 'analysis':
        yield ThinkingStep(
            title='Xác định khung phân tích' if vi else 'Defining analysis framework',
            description=(
                f'Đối tượng phân tích: {kw_str}. '
                'Xác định các tiêu chí đánh giá, thu thập dữ liệu liên quan '
                'và xây dựng góc nhìn đa chiều.'
            ) if vi else (
                f'Analysis subject: {kw_str}. '
                'Defining evaluation criteria, gathering relevant data, '
                'and building multi-dimensional perspective.'
            ),
            duration_ms=400, category=category,
        )
        yield ThinkingStep(
            title='Tổng hợp và đánh giá' if vi else 'Synthesizing and evaluating',
            description=(
                'Liên kết các dữ liệu đã phân tích, đánh giá ưu nhược điểm '
                'và rút ra kết luận dựa trên bằng chứng.'
            ) if vi else (
                'Connecting analyzed data, evaluating strengths and weaknesses, '
                'and drawing evidence-based conclusions.'
            ),
            duration_ms=350, category=category,
        )

    elif category == 'creative':
        yield ThinkingStep(
            title='Phát triển ý tưởng sáng tạo' if vi else 'Developing creative concept',
            description=(
                f'Chủ đề sáng tạo liên quan đến: {kw_str}. '
                'Xây dựng cấu trúc nội dung, xác định phong cách và giọng văn phù hợp.'
            ) if vi else (
                f'Creative topic: {kw_str}. '
                'Building content structure, defining appropriate style and tone.'
            ),
            duration_ms=400, category=category,
        )
        yield ThinkingStep(
            title='Hoàn thiện nội dung' if vi else 'Refining content',
            description=(
                'Phát triển chi tiết ý tưởng, đảm bảo logic mạch lạc '
                'và tính sáng tạo trong cách thể hiện.'
            ) if vi else (
                'Developing idea details, ensuring logical coherence '
                'and creative expression.'
            ),
            duration_ms=300, category=category,
        )

    elif category == 'math':
        yield ThinkingStep(
            title='Nhận diện bài toán' if vi else 'Identifying the problem',
            description=(
                f'Bài toán liên quan đến: {kw_str}. '
                'Xác định dạng bài, các biến số, điều kiện ràng buộc '
                'và phương pháp giải phù hợp nhất.'
            ) if vi else (
                f'Problem involves: {kw_str}. '
                'Identifying problem type, variables, constraints, '
                'and selecting the most appropriate solving method.'
            ),
            duration_ms=400, category=category,
        )
        yield ThinkingStep(
            title='Thực hiện giải bài toán' if vi else 'Solving step by step',
            description=(
                'Áp dụng phương pháp đã chọn, thực hiện tính toán từng bước '
                'và kiểm tra tính hợp lệ của kết quả.'
            ) if vi else (
                'Applying chosen method, performing step-by-step calculations, '
                'and verifying result validity.'
            ),
            duration_ms=350, category=category,
        )

    elif category == 'translate':
        yield ThinkingStep(
            title='Phân tích ngữ cảnh dịch thuật' if vi else 'Analyzing translation context',
            description=(
                'Xác định ngôn ngữ nguồn và đích, phân tích ngữ cảnh, '
                'sắc thái văn hóa và giọng điệu phù hợp cho bản dịch.'
            ) if vi else (
                'Identifying source and target languages, analyzing context, '
                'cultural nuances, and appropriate tone for translation.'
            ),
            duration_ms=350, category=category,
        )
        yield ThinkingStep(
            title='Chuyển đổi ngôn ngữ' if vi else 'Performing translation',
            description=(
                'Dịch thuật tự nhiên, giữ nguyên ý nghĩa gốc, '
                'đảm bảo câu văn trôi chảy trong ngôn ngữ đích.'
            ) if vi else (
                'Natural translation preserving original meaning, '
                'ensuring fluent expression in target language.'
            ),
            duration_ms=300, category=category,
        )

    elif category == 'summary':
        yield ThinkingStep(
            title='Xác định nội dung chính' if vi else 'Identifying key content',
            description=(
                f'Đọc và phân tích nội dung liên quan đến: {kw_str}. '
                'Lọc ra các ý chính, bỏ qua chi tiết phụ.'
            ) if vi else (
                f'Reading and analyzing content related to: {kw_str}. '
                'Filtering main ideas, omitting secondary details.'
            ),
            duration_ms=350, category=category,
        )
        yield ThinkingStep(
            title='Cô đọng thông tin' if vi else 'Condensing information',
            description=(
                'Tóm tắt các điểm quan trọng nhất một cách ngắn gọn, '
                'giữ nguyên ý nghĩa cốt lõi và cấu trúc logic.'
            ) if vi else (
                'Summarizing the most important points concisely, '
                'preserving core meaning and logical structure.'
            ),
            duration_ms=300, category=category,
        )

    elif category == 'planning':
        yield ThinkingStep(
            title='Phân tích yêu cầu kế hoạch' if vi else 'Analyzing planning requirements',
            description=(
                f'Mục tiêu liên quan đến: {kw_str}. '
                'Xác định phạm vi, nguồn lực, timeline và các yếu tố rủi ro cần xem xét.'
            ) if vi else (
                f'Goals relate to: {kw_str}. '
                'Defining scope, resources, timeline, and risk factors to consider.'
            ),
            duration_ms=400, category=category,
        )
        yield ThinkingStep(
            title='Xây dựng lộ trình' if vi else 'Building roadmap',
            description=(
                'Thiết kế các bước hành động cụ thể, '
                'sắp xếp theo thứ tự ưu tiên và mốc thời gian hợp lý.'
            ) if vi else (
                'Designing specific action steps, '
                'prioritizing and setting reasonable milestones.'
            ),
            duration_ms=350, category=category,
        )

    elif category == 'research':
        yield ThinkingStep(
            title='Xác định phạm vi nghiên cứu' if vi else 'Scoping the research',
            description=(
                f'Chủ đề nghiên cứu: {kw_str}. '
                'Thu thập kiến thức nền tảng, xác định nguồn thông tin đáng tin cậy '
                'và các khía cạnh cần tìm hiểu.'
            ) if vi else (
                f'Research topic: {kw_str}. '
                'Gathering foundational knowledge, identifying reliable sources, '
                'and aspects to explore.'
            ),
            duration_ms=400, category=category,
        )
        yield ThinkingStep(
            title='Tổng hợp kết quả' if vi else 'Synthesizing findings',
            description=(
                'Kết nối thông tin từ nhiều nguồn, '
                'đánh giá độ tin cậy và trình bày kết quả có cấu trúc.'
            ) if vi else (
                'Connecting information from multiple sources, '
                'evaluating reliability, and presenting structured findings.'
            ),
            duration_ms=350, category=category,
        )

    elif category in ('question', 'opinion'):
        yield ThinkingStep(
            title='Phân tích câu hỏi' if vi else 'Analyzing the question',
            description=(
                f'Câu hỏi liên quan đến: {kw_str}. '
                'Xác định thông tin cần thiết để đưa ra câu trả lời chính xác và đầy đủ.'
            ) if vi else (
                f'Question relates to: {kw_str}. '
                'Determining information needed for an accurate and complete answer.'
            ),
            duration_ms=350, category=category,
        )
        yield ThinkingStep(
            title='Xây dựng câu trả lời' if vi else 'Formulating answer',
            description=(
                'Thu thập và liên kết thông tin liên quan, '
                'đảm bảo câu trả lời có cơ sở và dễ hiểu.'
            ) if vi else (
                'Gathering and connecting relevant information, '
                'ensuring the answer is well-founded and clear.'
            ),
            duration_ms=300, category=category,
        )

    else:
        # general / complex
        yield ThinkingStep(
            title='Xử lý yêu cầu' if vi else 'Processing request',
            description=(
                f'Nội dung yêu cầu xoay quanh: {kw_str}. '
                'Phân tích ngữ cảnh, xác định cách tiếp cận phù hợp nhất '
                'để đưa ra phản hồi chất lượng.'
            ) if vi else (
                f'Request content revolves around: {kw_str}. '
                'Analyzing context, determining the most appropriate approach '
                'for a quality response.'
            ),
            duration_ms=350, category=category,
        )

    # ═══ Deep thinking extra steps ═══
    if deep_thinking:
        yield ThinkingStep(
            title='Phân tích sâu đa chiều' if vi else 'Deep multi-perspective analysis',
            description=(
                'Xem xét vấn đề từ nhiều góc độ khác nhau. '
                'Cân nhắc các giả thuyết thay thế, phản biện và bổ sung '
                'để đảm bảo phản hồi toàn diện.'
            ) if vi else (
                'Examining the problem from multiple perspectives. '
                'Considering alternative hypotheses, counterarguments, '
                'and supplements for a comprehensive response.'
            ),
            duration_ms=450, category=category,
        )
        yield ThinkingStep(
            title='Đánh giá phương án' if vi else 'Evaluating approaches',
            description=(
                'So sánh ưu nhược điểm của các phương án khác nhau, '
                'xác định giải pháp tối ưu dựa trên ngữ cảnh và yêu cầu cụ thể.'
            ) if vi else (
                'Comparing pros and cons of different approaches, '
                'identifying optimal solution based on specific context and requirements.'
            ),
            duration_ms=400, category=category,
        )

    # ═══ Final step: composing ═══
    context_labels = {
        'casual': 'thoải mái, thân thiện' if vi else 'casual, friendly',
        'programming': 'kỹ thuật, chính xác' if vi else 'technical, precise',
        'creative': 'sáng tạo, phong phú' if vi else 'creative, rich',
        'research': 'học thuật, có nguồn dẫn' if vi else 'academic, well-sourced',
        'psychological': 'đồng cảm, hỗ trợ' if vi else 'empathetic, supportive',
        'lifestyle': 'gần gũi, thực tế' if vi else 'relatable, practical',
    }
    ctx_label = context_labels.get(context, context)
    yield ThinkingStep(
        title='Tổng hợp câu trả lời' if vi else 'Composing response',
        description=(
            f'Hoàn thiện câu trả lời với phong cách {ctx_label}, '
            'đảm bảo nội dung chính xác, rõ ràng và hữu ích cho người dùng.'
        ) if vi else (
            f'Finalizing response in {ctx_label} style, '
            'ensuring accurate, clear, and helpful content for the user.'
        ),
        duration_ms=250, category=category,
    )


def detect_category(message: str) -> str:
    """Detect the category of a message"""
    category, _ = _detect_intent(message)
    return category


def generate_thinking_summary(
    message: str,
    category: str,
    language: str = 'vi',
) -> str:
    """Generate a brief summary of the thinking process"""
    vi = language == 'vi'
    summaries = {
        'greeting': ('Đã phân tích và chuẩn bị phản hồi',
                     'Analyzed and prepared response'),
        'code': ('Đã phân tích yêu cầu kỹ thuật và thiết kế giải pháp',
                 'Analyzed technical requirements and designed solution'),
        'explain': ('Đã xây dựng giải thích có cấu trúc',
                    'Built structured explanation'),
        'analysis': ('Đã phân tích đa chiều và tổng hợp kết luận',
                     'Multi-dimensional analysis and synthesis complete'),
        'creative': ('Đã phát triển ý tưởng và hoàn thiện nội dung',
                     'Developed ideas and refined content'),
        'math': ('Đã giải quyết bài toán theo từng bước',
                 'Solved problem step by step'),
        'translate': ('Đã phân tích và chuyển đổi ngôn ngữ',
                      'Analyzed and translated'),
        'summary': ('Đã xác định và cô đọng nội dung chính',
                    'Identified and condensed key content'),
        'planning': ('Đã phân tích yêu cầu và xây dựng lộ trình',
                     'Analyzed requirements and built roadmap'),
        'research': ('Đã nghiên cứu và tổng hợp kiến thức',
                     'Researched and synthesized knowledge'),
        'question': ('Đã phân tích câu hỏi và xây dựng câu trả lời',
                     'Analyzed question and built answer'),
        'opinion': ('Đã đánh giá và chuẩn bị gợi ý',
                    'Evaluated and prepared recommendation'),
        'general': ('Đã phân tích và chuẩn bị câu trả lời',
                    'Analyzed and prepared response'),
        'complex': ('Đã phân tích yêu cầu phức tạp và hoàn thiện phản hồi',
                    'Analyzed complex request and prepared response'),
    }
    pair = summaries.get(category, summaries['general'])
    return pair[0] if vi else pair[1]
