# 🧪 AI-Assistant Test Suite

Comprehensive testing suite for the AI-Assistant project using pytest with mock testing for external services.

## 📋 Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Installation](#installation)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Mock Testing](#mock-testing)
- [Coverage Reports](#coverage-reports)
- [Writing New Tests](#writing-new-tests)

## 🎯 Overview

This test suite provides comprehensive coverage for:

### Core Services
- ✅ **Hub Gateway** - Main coordinator service
- ✅ **ChatBot Service** - AI chatbot with multi-model support (Gemini, OpenAI)
- ✅ **Text2SQL Service** - Natural language to SQL conversion

### Additional Services
- ✅ **Document Intelligence** - OCR and document analysis (PaddleOCR + Gemini)
- ✅ **Speech2Text** - Audio transcription and speaker diarization
- ✅ **LoRA Training Tool** - Fine-tuning diffusion models with LoRA
- ✅ **Image Upscale Tool** - AI-powered upscaling (Real-ESRGAN, SwinIR, ScuNET)
- ✅ **Stable Diffusion WebUI** - Text-to-image and image-to-image generation

### Infrastructure
- ✅ **Utilities** - Cache, rate limiting, error handling
- ✅ **API Endpoints** - All REST API routes
- ✅ **Integration** - Service interactions and workflows

**Total Test Cases: 330+**

**Key Features:**
- 🎭 **Mock Testing**: All external APIs (Gemini, OpenAI, MongoDB, Whisper, etc.) are mocked
- 📊 **Coverage Reports**: HTML and terminal coverage reporting (85%+ target)
- 🚀 **Fast Execution**: Unit tests run in seconds
- 🔄 **CI/CD Ready**: Configured for continuous integration
- 📦 **Isolated**: Tests don't require actual API keys or databases

## 📁 Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── __init__.py
│
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_hub.py          # Hub Gateway tests (50+ tests)
│   ├── test_chatbot.py      # ChatBot service tests (40+ tests)
│   ├── test_text2sql.py     # Text2SQL service tests (35+ tests)
│   ├── test_document_intelligence.py  # Document Intelligence (80+ tests)
│   ├── test_speech2text.py  # Speech2Text service (70+ tests)
│   ├── test_lora_training.py  # LoRA Training tool (40+ tests)
│   ├── test_upscale_tool.py   # Image upscale tool (35+ tests)
│   └── test_stable_diffusion.py  # Stable Diffusion WebUI (40+ tests)
│
├── integration/             # Integration tests (service interactions)
│   └── test_api_integration.py  # All service integration tests
│
├── fixtures/                # Test data and fixtures
│   └── sample_data.py       # Sample conversations, schemas, etc.
│
└── mocks/                   # Mock objects for external services
    └── __init__.py          # Gemini, OpenAI, MongoDB, Whisper mocks
```

## 🛠️ Installation

### 1. Install Test Dependencies

```bash
# Activate your virtual environment first
.\venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Install test dependencies
pip install -r requirements-test.txt
```

### 2. Verify Installation

```bash
pytest --version
```

Should show: `pytest 7.4.0` or higher

## 🚀 Running Tests

### Quick Start (Recommended)

**Windows:**
```bash
.\run-tests.bat
```

**Linux/Mac:**
```bash
chmod +x run-tests.sh
./run-tests.sh
```

This will:
1. ✅ Install dependencies
2. ✅ Run all tests with coverage
3. ✅ Generate HTML coverage report
4. ✅ Automatically open report in browser

### Manual Execution

**Run all tests:**
```bash
pytest
```

**Run with verbose output:**
```bash
pytest -v
```

**Run with coverage:**
```bash
pytest --cov=src --cov=ChatBot/src --cov-report=html --cov-report=term-missing
```

**Run specific test file:**
```bash
pytest tests/unit/test_hub.py
pytest tests/unit/test_chatbot.py
pytest tests/integration/test_api_integration.py
```

**Run specific test class:**
```bash
pytest tests/unit/test_hub.py::TestHubGateway
```

**Run specific test function:**
```bash
pytest tests/unit/test_hub.py::TestHubGateway::test_index_route
```

### Using Test Runner Script

```bash
# Run all tests
python scripts/test_runner.py all

# Run only unit tests
python scripts/test_runner.py unit

# Run only integration tests
python scripts/test_runner.py integration

# Run specific service tests
python scripts/test_runner.py hub
python scripts/test_runner.py chatbot
python scripts/test_runner.py text2sql

# Run smoke tests (quick validation)
python scripts/test_runner.py smoke

# Run fast tests only (exclude slow tests)
python scripts/test_runner.py fast

# With coverage
python scripts/test_runner.py all --coverage

# Verbose output
python scripts/test_runner.py all --verbose

# Stop on first failure
python scripts/test_runner.py all --failfast
```

## 🏷️ Test Categories

Tests are organized with pytest markers:

### By Type

**Unit Tests** (fast, isolated):
```bash
pytest -m unit
```

**Integration Tests** (service interactions):
```bash
pytest -m integration
```

**API Tests** (endpoint testing):
```bash
pytest -m api
```

**Smoke Tests** (quick validation):
```bash
pytest -m smoke
```

### By Service

**Hub Gateway Tests:**
```bash
pytest -m hub
```

**ChatBot Tests:**
```bash
pytest -m chatbot
```

**Text2SQL Tests:**
```bash
pytest -m text2sql
```

### By Speed

**Fast tests only:**
```bash
pytest -m "not slow"
```

**Slow tests only:**
```bash
pytest -m slow
```

## 🎭 Mock Testing

All external services are **mocked** - no real API calls are made during testing!

### What's Mocked?

✅ **Google Gemini API** - AI model responses  
✅ **OpenAI API** - GPT model responses  
✅ **MongoDB** - Database operations  
✅ **Stable Diffusion** - Image generation  
✅ **ImgBB** - Image upload service  
✅ **HTTP Requests** - All external HTTP calls  

### Using Mocks in Tests

```python
import pytest

def test_with_gemini_mock(mock_gemini_model):
    """Example using Gemini mock"""
    response = mock_gemini_model.generate_content("Test prompt")
    assert response.text == "This is a mocked Gemini response"

def test_with_mongodb_mock(mock_mongodb):
    """Example using MongoDB mock"""
    db = mock_mongodb['test_db']
    collection = db['test_collection']
    
    result = collection.insert_one({'name': 'Test'})
    assert result.inserted_id is not None

@patch('requests.post')
def test_with_http_mock(mock_post):
    """Example using HTTP mock"""
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {'success': True}
    )
    # Your test code here
```

### Available Mock Fixtures

From `conftest.py`:
- `mock_gemini_model` - Google Gemini AI
- `mock_openai_client` - OpenAI GPT
- `mock_mongodb` - MongoDB client
- `mock_requests` - HTTP requests (get/post)
- `mock_cache` - Cache manager
- `mock_database` - Database manager

From `tests/mocks/__init__.py`:
- `MockGeminiModel`
- `MockOpenAIClient`
- `MockMongoDBClient`
- `MockStableDiffusionAPI`
- `MockImgBBUploader`
- And more...

## 📊 Coverage Reports

### Terminal Coverage

Run tests with coverage:
```bash
pytest --cov=src --cov=ChatBot/src --cov-report=term-missing
```

Shows coverage percentage with missing lines highlighted.

### HTML Coverage Report

```bash
pytest --cov=src --cov-report=html
```

Then open: `htmlcov/index.html` in your browser

**Features:**
- 📊 Line-by-line coverage visualization
- 🎨 Color-coded coverage levels
- 🔍 Detailed file-by-file breakdown
- 📈 Branch coverage analysis

### Coverage Configuration

Edit `pytest.ini` to customize:
- Source directories to analyze
- Directories to exclude
- Coverage thresholds
- Report formats

## ✍️ Writing New Tests

### 1. Choose Test Type

**Unit Test** - Testing a single function/class:
```python
# tests/unit/test_mymodule.py
import pytest

@pytest.mark.unit
def test_my_function():
    result = my_function(input_data)
    assert result == expected_output
```

**Integration Test** - Testing service interactions:
```python
# tests/integration/test_my_integration.py
import pytest

@pytest.mark.integration
def test_service_workflow(hub_client):
    response = hub_client.get('/api/endpoint')
    assert response.status_code == 200
```

### 2. Use Fixtures

```python
def test_with_fixtures(hub_client, sample_data, mock_gemini):
    # Fixtures are automatically injected
    response = hub_client.post('/api/chat', json=sample_data)
    assert response.status_code == 200
```

### 3. Add Test Markers

```python
@pytest.mark.unit
@pytest.mark.hub
@pytest.mark.slow  # If test takes >1 second
def test_something():
    pass
```

### 4. Test Structure Best Practices

```python
def test_descriptive_name():
    # Arrange - Set up test data
    input_data = {'key': 'value'}
    expected = 'result'
    
    # Act - Execute the code being tested
    result = function_under_test(input_data)
    
    # Assert - Verify the results
    assert result == expected
```

### 5. Testing Exceptions

```python
def test_raises_exception():
    with pytest.raises(ValueError):
        function_that_should_raise_error()

def test_exception_message():
    with pytest.raises(ValueError, match="Invalid input"):
        function_with_specific_error()
```

### 6. Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input, expected):
    assert input * 2 == expected
```

## 🎯 Next Steps After Tests Pass

### If All Tests Pass ✅

Great! Your code is working correctly with mocked services. Now:

1. **Deploy to Staging**: Test with real APIs in a staging environment
2. **Integration Testing**: Test actual API integrations
3. **Performance Testing**: Check response times and resource usage
4. **Security Testing**: Validate security measures
5. **User Acceptance Testing**: Get feedback from end users

### Setting Up Real API Integration

Once tests pass with mocks, configure real APIs:

```bash
# Create .env file with real credentials
GEMINI_API_KEY=your_real_gemini_key
OPENAI_API_KEY=your_real_openai_key
MONGODB_URI=your_real_mongodb_connection
```

Then test manually:
```bash
# Start services
python src/hub.py
cd ChatBot && python app.py
cd "Text2SQL Services" && python app_simple.py
```

### Continuous Integration

Add to your CI/CD pipeline:

```yaml
# .github/workflows/test.yml (GitHub Actions example)
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

## 🆘 Troubleshooting

### Tests fail with import errors

```bash
# Make sure you're in the project root
cd AI-Assistant

# Activate virtual environment
.\venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt -r requirements-test.txt
```

### MongoDB connection errors

**This is expected!** Tests use mocks, not real MongoDB. If you see errors:
- Check that `MONGODB_ENABLED=False` in test environment
- Verify `conftest.py` patches MongoDB correctly

### API key errors

**This is also expected!** Tests use mock API keys. Real keys are not needed.

### Coverage not generated

```bash
# Make sure pytest-cov is installed
pip install pytest-cov

# Run with explicit coverage options
pytest --cov=src --cov-report=html
```

## 📝 Summary

✅ **300+ test cases** covering all major functionality  
✅ **Mock testing** - No real API calls needed  
✅ **Fast execution** - Unit tests run in seconds  
✅ **Coverage reports** - Know what's tested  
✅ **Easy to extend** - Clear patterns for new tests  

**Happy Testing! 🎉**
