import json
import re
from typing import Any, Type
from fastapi import HTTPException
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

def clean_json_text(text: str) -> str:
    """Clean markdown code fences from JSON output."""
    text = text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
    return text

def extract_content_text(content: Any) -> str:
    """Extract plain text from LangChain message content, filtering thinking chunks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict):
                if part.get('type') == 'text' and not part.get('extras', {}).get('thought'):
                    text_parts.append(part.get('text', ''))
        return ''.join(text_parts)
    return str(content)

def get_chat_model(settings, temperature: float = 0.1):
    """Factory to get configured ChatGoogleGenerativeAI instance."""
    if not settings.gemini_api_key:
        raise HTTPException(503, 'Gemini is not configured. Add GEMINI_API_KEY in the backend secret settings.')
    if not settings.gemini_free_tier_confirmed:
        raise HTTPException(503, 'Confirm the Gemini project uses the free tier before enabling AI.')
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=temperature
    )

async def call_llm_structured(settings, system_prompt: str, user_prompt: str, schema_class: Type[BaseModel], temperature: float = 0.1) -> BaseModel:
    """Invoke Gemini with strict system instruction and parse response into Pydantic schema."""
    llm = get_chat_model(settings, temperature=temperature)
    schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
    augmented_system = f"{system_prompt}\n\nYou MUST respond ONLY with valid JSON conforming to the following JSON Schema. Do not wrap in markdown or include conversational text.\nSchema:\n{schema_json}"
    
    messages = [
        SystemMessage(content=augmented_system),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = await llm.ainvoke(messages)
        raw_text = clean_json_text(extract_content_text(response.content))
        return schema_class.model_validate_json(raw_text)
    except Exception as e:
        err_msg = str(e)
        if '429' in err_msg or 'RESOURCE_EXHAUSTED' in err_msg:
            raise HTTPException(429, 'Gemini quota reached. Try later; no paid fallback is enabled.')
        # Fallback regex extraction if model included outer commentary
        match = re.search(r'(\{[\s\S]*\})', extract_content_text(getattr(response, 'content', '')))
        if match:
            try:
                return schema_class.model_validate_json(match.group(1))
            except Exception:
                pass
        raise HTTPException(502, f"AI agent structured output failed validation: {err_msg}")
