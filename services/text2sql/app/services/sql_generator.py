"""
SQL Generator Service
Multi-model SQL generation (Gemini, GROK, OpenAI, DeepSeek)
"""

import os
import re
import logging
from typing import Optional
import openai

logger = logging.getLogger(__name__)


class SQLGeneratorService:
    """Service for generating SQL from natural language using various AI models."""
    
    def __init__(self, config=None):
        """
        Initialize SQL Generator with configuration.
        
        Args:
            config: Application configuration object
        """
        self.config = config or {}
        self._gemini_client = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialize AI clients."""
        from ..extensions import get_gemini_client
        self._gemini_client = get_gemini_client()
    
    def generate_sql(self, schema_text: str, question: str, model: str = None) -> str:
        """
        Generate SQL using the specified model.
        
        Args:
            schema_text: Database schema(s)
            question: Natural language question
            model: AI model to use (gemini, grok, openai, deepseek)
        
        Returns:
            Generated SQL query
        """
        model = model or os.getenv('DEFAULT_SQL_MODEL', 'grok')
        
        generators = {
            'gemini': self._generate_with_gemini,
            'grok': self._generate_with_grok,
            'openai': self._generate_with_openai,
            'deepseek': self._generate_with_deepseek
        }
        
        generator = generators.get(model.lower())
        if not generator:
            raise ValueError(f"Unsupported model: {model}")
        
        sql = generator(schema_text, question)
        return self._clean_sql(sql)
    
    def refine_sql(self, schema_text: str, question: str, 
                   prev_sql: str, feedback: str = None, 
                   extra_context: str = None, model: str = None) -> str:
        """
        Refine an existing SQL query based on feedback.
        
        Args:
            schema_text: Database schema(s)
            question: Original question
            prev_sql: Previous SQL query that needs improvement
            feedback: What was wrong with the previous query
            extra_context: Additional constraints or notes
            model: AI model to use
        
        Returns:
            Refined SQL query
        """
        model = model or os.getenv('REFINE_STRATEGY', 'gemini')
        
        if model.lower() == 'grok':
            sql = self._refine_with_grok(schema_text, question, prev_sql, feedback, extra_context)
        else:
            sql = self._refine_with_gemini(schema_text, question, prev_sql, feedback, extra_context)
        
        return self._clean_sql(sql)
    
    def _generate_with_gemini(self, schema_text: str, question: str) -> str:
        """Generate SQL using Gemini."""
        if not self._gemini_client:
            from ..extensions import get_gemini_client
            self._gemini_client = get_gemini_client()
        
        if not self._gemini_client:
            raise ValueError("Gemini client not configured")
        
        prompt = f"""
You are an SQL expert.
Here is/are database schema(s):

{schema_text}

User question: {question}

Write a valid SQL query (ClickHouse style).
Do not explain, just output the SQL.
"""
        resp = self._gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return resp.text.strip()
    
    def _generate_with_grok(self, schema_text: str, question: str) -> str:
        """Generate SQL using GROK API (xAI)."""
        api_key = os.getenv('GROK_API_KEY')
        if not api_key:
            raise ValueError("GROK_API_KEY not configured")
        
        prompt = f"""You are an expert SQL engineer specialized in ClickHouse.

Database schema(s):
{schema_text}

User question: {question}

Write a valid SQL query for ClickHouse.
- Return ONLY the SQL query, no explanation.
- If it's a SELECT without explicit LIMIT, add LIMIT 20.
- Use proper ClickHouse syntax.
"""
        
        client = openai.OpenAI(
            api_key=api_key,
            base_url='https://api.x.ai/v1'
        )
        
        response = client.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": "You are an expert SQL engineer. Output ONLY valid SQL queries without any explanation or markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
    
    def _generate_with_openai(self, schema_text: str, question: str) -> str:
        """Generate SQL using OpenAI GPT-4."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        prompt = f"""You are an expert SQL query generator. Given the following database schema and question, generate a valid SQL query.

Database Schema:
{schema_text}

Question: {question}

Generate ONLY the SQL query without any explanation. The query should be valid and optimized."""
        
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert SQL query generator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
    
    def _generate_with_deepseek(self, schema_text: str, question: str) -> str:
        """Generate SQL using DeepSeek."""
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not configured")
        
        prompt = f"""You are an expert SQL query generator. Given the following database schema and question, generate a valid SQL query.

Database Schema:
{schema_text}

Question: {question}

Generate ONLY the SQL query without any explanation. The query should be valid and optimized."""
        
        client = openai.OpenAI(
            api_key=api_key,
            base_url='https://api.deepseek.com'
        )
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are an expert SQL query generator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
    
    def _refine_with_gemini(self, schema_text: str, question: str,
                            prev_sql: str, feedback: str, extra_context: str) -> str:
        """Refine SQL using Gemini."""
        if not self._gemini_client:
            from ..extensions import get_gemini_client
            self._gemini_client = get_gemini_client()
        
        if not self._gemini_client:
            raise ValueError("Gemini client not configured")
        
        fb = (feedback or "").strip()
        extra = (extra_context or "").strip()
        
        prompt = f"""
You are an advanced SQL engineer specialized in ClickHouse.

Database schema(s):
{schema_text}

User question:
{question}

Previous SQL (needs fix):
{prev_sql}

Short critique of what's wrong:
{fb if fb else "The previous SQL did not fully answer the question."}

Additional user notes / constraints to apply:
{extra if extra else "(no additional notes)"}

Revise the SQL so that it correctly answers the question.
Constraints:
- Use ClickHouse SQL dialect.
- Keep it as a single final query if possible.
- Return ONLY the final SQL, no explanation.
"""
        resp = self._gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return resp.text.strip()
    
    def _refine_with_grok(self, schema_text: str, question: str,
                          prev_sql: str, feedback: str, extra_context: str) -> str:
        """Refine SQL using GROK."""
        api_key = os.getenv('GROK_API_KEY')
        if not api_key:
            raise ValueError("GROK_API_KEY not configured")
        
        fb = (feedback or "").strip()
        extra = (extra_context or "").strip()
        
        prompt = f"""You are an advanced SQL engineer specialized in ClickHouse.

Database schema(s):
{schema_text}

User question:
{question}

Previous SQL (needs fix):
{prev_sql}

Short critique of what's wrong:
{fb if fb else "The previous SQL did not fully answer the question."}

Additional user notes / constraints to apply:
{extra if extra else "(no additional notes)"}

Revise the SQL so that it correctly answers the question.
Constraints:
- Use ClickHouse SQL dialect.
- Keep it as a single final query if possible.
- Return ONLY the final SQL, no explanation.
"""
        
        client = openai.OpenAI(
            api_key=api_key,
            base_url='https://api.x.ai/v1'
        )
        
        response = client.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": "You are an expert SQL engineer. Output ONLY valid SQL queries without any explanation or markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
    
    def _clean_sql(self, sql: str) -> str:
        """Clean SQL output from markdown fences and extra whitespace."""
        if not sql:
            return ""
        
        # Remove markdown code fences
        sql = re.sub(r'^```(?:sql)?\s*', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'\s*```$', '', sql, flags=re.MULTILINE)
        
        return sql.strip()
