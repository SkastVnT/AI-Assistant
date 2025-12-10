# 🔧 Hướng dẫn tích hợp Tools vào ChatBot

## 📋 Tổng quan

ChatBot hiện tại hỗ trợ 2 tools:
1. **Google Search** 🔍 - Tìm kiếm thông tin real-time
2. **GitHub Connector** - Truy vấn repositories, code, issues

Hiện tại tools chỉ được **đánh dấu trong message**, chưa thực sự gọi API. Dưới đây là hướng dẫn tích hợp đầy đủ.

---

## 🔍 1. Google Search Integration

### Option A: Google Custom Search API (Miễn phí 100 queries/ngày)

#### Bước 1: Đăng ký API Key

1. Truy cập: https://developers.google.com/custom-search/v1/introduction
2. Click **Get a Key** → Tạo project mới
3. Copy **API Key**
4. Tạo Custom Search Engine: https://programmablesearchengine.google.com/
5. Copy **Search Engine ID (cx)**

#### Bước 2: Cài đặt thư viện

```bash
pip install google-api-python-client
```

#### Bước 3: Thêm vào .env

```properties
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_search_engine_id_here
```

#### Bước 4: Implement trong app.py

```python
from googleapiclient.discovery import build
import os

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')

def google_search(query, num_results=5):
    """Search Google and return results"""
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        result = service.cse().list(q=query, cx=GOOGLE_CSE_ID, num=num_results).execute()
        
        search_results = []
        for item in result.get('items', []):
            search_results.append({
                'title': item['title'],
                'link': item['link'],
                'snippet': item['snippet']
            })
        
        return search_results
    except Exception as e:
        return [{'error': str(e)}]
```

#### Bước 5: Sử dụng trong chat

```python
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    
    # Check if Google Search tool is active
    if '[Tools: google-search' in message:
        # Extract actual query
        query = message.split('[Tools:')[0].strip()
        
        # Perform search
        search_results = google_search(query)
        
        # Add results to context
        context_addition = "\n\n**Kết quả tìm kiếm Google:**\n"
        for idx, result in enumerate(search_results, 1):
            context_addition += f"{idx}. [{result['title']}]({result['link']})\n"
            context_addition += f"   {result['snippet']}\n\n"
        
        message = query + context_addition
    
    # Continue with normal chat flow...
```

### Option B: SerpAPI (Paid, dễ hơn)

```bash
pip install google-search-results
```

```python
from serpapi import GoogleSearch

def google_search_serpapi(query):
    params = {
        "q": query,
        "api_key": os.getenv('SERPAPI_KEY'),
        "num": 5
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return results.get('organic_results', [])
```

**Giá:** $50/tháng cho 5,000 searches

---

## 🐙 2. GitHub Connector Integration

### Bước 1: Tạo GitHub Personal Access Token

1. Truy cập: https://github.com/settings/tokens
2. Click **Generate new token (classic)**
3. Chọn scopes:
   - `repo` - Full control of repositories
   - `read:org` - Read organization data
   - `read:user` - Read user profile
4. Copy token

### Bước 2: Cài đặt PyGithub

```bash
pip install PyGithub
```

### Bước 3: Thêm vào .env

```properties
GITHUB_TOKEN=ghp_your_github_token_here
```

### Bước 4: Implement trong app.py

```python
from github import Github
import os

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

def search_github_repos(query, max_results=5):
    """Search GitHub repositories"""
    try:
        g = Github(GITHUB_TOKEN)
        repos = g.search_repositories(query=query)
        
        results = []
        for repo in repos[:max_results]:
            results.append({
                'name': repo.full_name,
                'description': repo.description,
                'stars': repo.stargazers_count,
                'url': repo.html_url,
                'language': repo.language
            })
        
        return results
    except Exception as e:
        return [{'error': str(e)}]

def search_github_code(query, language=None, max_results=5):
    """Search code in GitHub"""
    try:
        g = Github(GITHUB_TOKEN)
        search_query = query
        if language:
            search_query += f" language:{language}"
        
        code_results = g.search_code(query=search_query)
        
        results = []
        for code in code_results[:max_results]:
            results.append({
                'file': code.path,
                'repo': code.repository.full_name,
                'url': code.html_url
            })
        
        return results
    except Exception as e:
        return [{'error': str(e)}]

def get_repo_info(repo_name):
    """Get detailed info about a repository"""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(repo_name)
        
        return {
            'name': repo.full_name,
            'description': repo.description,
            'stars': repo.stargazers_count,
            'forks': repo.forks_count,
            'language': repo.language,
            'topics': repo.get_topics(),
            'url': repo.html_url,
            'readme': repo.get_readme().decoded_content.decode('utf-8')[:500]  # First 500 chars
        }
    except Exception as e:
        return {'error': str(e)}
```

### Bước 5: Sử dụng trong chat

```python
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    
    # Check if GitHub tool is active
    if '[Tools: github' in message or '[Tools: google-search, github]' in message:
        query = message.split('[Tools:')[0].strip()
        
        # Search GitHub repos
        github_results = search_github_repos(query)
        
        context_addition = "\n\n**Kết quả GitHub:**\n"
        for repo in github_results:
            context_addition += f"- **[{repo['name']}]({repo['url']})** ⭐ {repo['stars']}\n"
            context_addition += f"  {repo['description']}\n"
            context_addition += f"  Language: {repo['language']}\n\n"
        
        message = query + context_addition
    
    # Continue with normal chat flow...
```

---

## 🚀 3. Nâng cao: Tool Calling với Gemini

Gemini 2.0 hỗ trợ **function calling** native:

```python
import google.generativeai as genai

# Define tools
tools = [
    {
        "function_declarations": [
            {
                "name": "google_search",
                "description": "Search Google for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_github",
                "description": "Search GitHub repositories",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Repository search query"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language filter"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
    }
]

# Use with model
model = genai.GenerativeModel('gemini-2.0-flash', tools=tools)
response = model.generate_content("Find me Python web frameworks on GitHub")

# Check if model wants to call a function
if response.candidates[0].content.parts[0].function_call:
    function_call = response.candidates[0].content.parts[0].function_call
    
    if function_call.name == "search_github":
        args = dict(function_call.args)
        results = search_github_repos(args['query'])
        
        # Send results back to model
        response = model.generate_content([
            response.candidates[0].content,
            genai.protos.Content(
                parts=[genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name="search_github",
                        response={"results": results}
                    )
                )]
            )
        ])
```

---

## 📊 So sánh Options

| Feature | Google CSE | SerpAPI | GitHub API |
|---------|-----------|---------|------------|
| **Giá** | Free 100/day | $50/mo | Free 5000/hr |
| **Dễ setup** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Chất lượng** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Rate limit** | 100/day | Based on plan | 5000/hour |

---

## 💡 Recommendation

**Cho $5 budget:**
1. ✅ **Google Custom Search API** - Free tier (100 queries/day đủ dùng)
2. ✅ **GitHub API** - Hoàn toàn free với Personal Access Token
3. ⚠️ Tránh SerpAPI trừ khi cần search quality cao

**Quick Start:**
```bash
# Install dependencies
pip install google-api-python-client PyGithub

# Add to .env
echo "GOOGLE_API_KEY=your_key" >> .env
echo "GOOGLE_CSE_ID=your_cx" >> .env
echo "GITHUB_TOKEN=your_token" >> .env

# Test
python test_tools.py
```

---

## 🔗 Links hữu ích

- Google Custom Search: https://developers.google.com/custom-search
- PyGithub Docs: https://pygithub.readthedocs.io/
- Gemini Function Calling: https://ai.google.dev/docs/function_calling
- SerpAPI: https://serpapi.com/

---

**Tác giả:** AI Assistant Team  
**Cập nhật:** October 28, 2025
