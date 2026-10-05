# notemd_core.py

import re
import httpx
import json
import logging
import math
import os
import asyncio
import tempfile
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, quote
from selectolax.lexbor import LexborHTMLParser
from markdown_processing import cleanup_latex_delimiters, ensure_mermaid_code_block, refine_mermaid_blocks, unwrap_markdown_response

logger = logging.getLogger(__name__)

# Placeholder for settings, will be imported from config.py
SETTINGS = {}

def set_settings(settings_dict):
    global SETTINGS
    SETTINGS = settings_dict

# --- Utility Functions (from utils.ts) ---
async def cancellable_delay(ms: int, cancelled: bool) -> None:
    if cancelled:
        raise asyncio.CancelledError("Processing cancelled")
    await asyncio.sleep(ms / 1000.0)
    if cancelled:
        raise asyncio.CancelledError("Processing cancelled")

def estimate_tokens(text: str) -> int:
    if not text: return 0
    return len(text) // 4

def get_provider_for_task(task_type: str) -> Optional[Dict[str, Any]]:
    provider_name = SETTINGS.get("ACTIVE_PROVIDER", "DeepSeek")
    if SETTINGS.get("USE_MULTI_MODEL_SETTINGS", False):
        provider_key_by_task = {
            "addLinks": "ADD_LINKS_PROVIDER",
            "research": "RESEARCH_PROVIDER",
            "generateTitle": "GENERATE_TITLE_PROVIDER",
            "translate": "TRANSLATE_PROVIDER",
            "summarizeToMermaid": "SUMMARIZE_TO_MERMAID_PROVIDER",
            "extractConcepts": "EXTRACT_CONCEPTS_PROVIDER",
            "extractOriginalText": "EXTRACT_ORIGINAL_TEXT_PROVIDER",
            "diagramGenerate": "DIAGRAM_PROVIDER",
        }
        provider_key = provider_key_by_task.get(task_type)
        if provider_key:
            provider_name = SETTINGS.get(provider_key, provider_name)

    for p in SETTINGS.get("DEFAULT_PROVIDERS", []) :
        if p["name"] == provider_name:
            return p
    return None

def get_model_for_task(task_type: str, provider_config: Dict[str, Any]) -> str:
    model_name = provider_config.get("model")
    if SETTINGS.get("USE_MULTI_MODEL_SETTINGS", False):
        model_key_by_task = {
            "addLinks": "ADD_LINKS_MODEL",
            "research": "RESEARCH_MODEL",
            "generateTitle": "GENERATE_TITLE_MODEL",
            "translate": "TRANSLATE_MODEL",
            "summarizeToMermaid": "SUMMARIZE_TO_MERMAID_MODEL",
            "extractConcepts": "EXTRACT_CONCEPTS_MODEL",
            "extractOriginalText": "EXTRACT_ORIGINAL_TEXT_MODEL",
            "diagramGenerate": "DIAGRAM_MODEL",
        }
        model_key = model_key_by_task.get(task_type)
        if model_key:
            model_name = SETTINGS.get(model_key) or model_name
    return model_name or ""

# --- Content Splitting (from utils.ts) ---
def split_content(content: str) -> List[str]:
    max_words = SETTINGS.get("CHUNK_WORD_COUNT", 3000)
    paragraphs = re.split(r'(\n\s*\n)', content)
    chunks = []
    current_chunk_parts = []
    current_word_count = 0

    def count_words(text: str) -> int:
        return len(re.findall(r'\b\w+\b', text.strip()))

    for part in paragraphs:
        part_word_count = count_words(part)

        if current_word_count + part_word_count > max_words and current_chunk_parts:
            chunks.append(''.join(current_chunk_parts).strip())
            current_chunk_parts = [part]
            current_word_count = part_word_count
        else:
            current_chunk_parts.append(part)
            current_word_count += part_word_count

    if current_chunk_parts:
        last_chunk = ''.join(current_chunk_parts).strip()
        if last_chunk:
            chunks.append(last_chunk)
    return chunks

# --- LLM Processing Prompt (from llmUtils.ts) ---
def get_llm_processing_prompt() -> str:
    return SETTINGS.get("CUSTOM_PROMPT_ADD_LINKS", "")

def resolve_language_display_name(language_code_or_name: str) -> str:
    if not language_code_or_name:
        return SETTINGS.get("LANGUAGE", "en")

    language = language_code_or_name.strip()
    for item in SETTINGS.get("AVAILABLE_LANGUAGES", []):
        if item.get("code") == language:
            return item.get("name") or language
    return language

def strip_boxed_wrapper(content: str) -> str:
    lines = content.split('\n')
    if lines and lines[0].strip() == '\\boxed{':
        lines.pop(0)
        if lines and lines[-1].strip() == '}':
            lines.pop()
    return '\n'.join(lines)

def apply_standard_post_processing(content: str, remove_markdown_fence: bool = False) -> str:
    if remove_markdown_fence:
        content = unwrap_markdown_response(content)
    processed = cleanup_latex_delimiters(content)
    processed = refine_mermaid_blocks(processed)
    processed = strip_boxed_wrapper(processed)
    return processed.strip()

def format_prompt(template: str, variables: Dict[str, str]) -> str:
    prompt = template
    for key, value in variables.items():
        prompt = prompt.replace(f"{{{key}}}", value)
    return prompt

# --- LLM API Call Implementations ---
async def execute_deepseek_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str) -> str:
    url = f"{provider_config['baseUrl']}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {provider_config['apiKey']}"}
    payload = {"model": model_name, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}], "temperature": provider_config['temperature'], "max_tokens": SETTINGS.get("MAX_TOKENS", 8192)}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

async def execute_openai_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str) -> str:
    url = f"{provider_config['baseUrl']}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {provider_config['apiKey']}"}
    payload = {"model": model_name, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}], "temperature": provider_config['temperature'], "max_tokens": SETTINGS.get("MAX_TOKENS", 8192)}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

async def execute_anthropic_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str) -> str:
    url = f"{provider_config['baseUrl']}/v1/messages"
    headers = {"Content-Type": "application/json", "x-api-key": provider_config['apiKey'], 'anthropic-version': '2023-06-01'}
    payload = {"model": model_name, "messages": [{"role": "user", "content": f"{prompt}\n\n{content}"}], "temperature": provider_config['temperature'], "max_tokens": SETTINGS.get("MAX_TOKENS", 8192)}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

async def execute_google_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str) -> str:
    # Credentials belong in headers: URLs are logged by HTTP clients and proxies.
    url = f"{provider_config['baseUrl']}/models/{model_name}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": provider_config['apiKey']}
    payload = {"contents": [{"role": "user", "parts": [{"text": f"{prompt}\n\n{content}"}]}], "generationConfig": {"temperature": provider_config['temperature'], "maxOutputTokens": SETTINGS.get("MAX_TOKENS", 8192)}}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

async def execute_mistral_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str) -> str:
    url = f"{provider_config['baseUrl']}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {provider_config['apiKey']}"}
    payload = {"model": model_name, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}], "temperature": provider_config['temperature'], "max_tokens": SETTINGS.get("MAX_TOKENS", 8192)}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

async def execute_azure_openai_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str) -> str:
    if not provider_config.get("apiVersion") or not provider_config.get("baseUrl"): raise ValueError('API version and Base URL are required for Azure OpenAI')
    url = f"{provider_config['baseUrl']}/openai/deployments/{model_name}/chat/completions?api-version={provider_config['apiVersion']}"
    headers = {"Content-Type": "application/json", "api-key": provider_config['apiKey']}
    payload = {"messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}], "temperature": provider_config['temperature'], "max_tokens": SETTINGS.get("MAX_TOKENS", 8192)}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

async def execute_lmstudio_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str) -> str:
    url = f"{provider_config['baseUrl']}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {provider_config.get('apiKey', 'EMPTY')}"}
    payload = {"model": model_name, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}], "temperature": provider_config['temperature'], "max_tokens": SETTINGS.get("MAX_TOKENS", 8192)}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

async def execute_ollama_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str) -> str:
    url = f"{provider_config['baseUrl']}/chat"
    headers = {"Content-Type": "application/json"}
    payload = {"model": model_name, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}], "options": {"temperature": provider_config['temperature'], "num_predict": SETTINGS.get("MAX_TOKENS", 8192)}, "stream": False}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

async def execute_openrouter_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str) -> str:
    url = f"{provider_config['baseUrl']}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {provider_config['apiKey']}", 'HTTP-Referer': 'https://github.com/Jacobinwwey/obsidian-NotEMD', 'X-Title': 'Notemd Obsidian Plugin'}
    payload = {"model": model_name, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}], "temperature": provider_config['temperature'], "max_tokens": SETTINGS.get("MAX_TOKENS", 8192)}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"].get("content") or data["choices"][0]["message"].get("reasoning")

API_CALL_FUNCTIONS = {
    "DeepSeek": execute_deepseek_api,
    "OpenAI": execute_openai_api,
    "Anthropic": execute_anthropic_api,
    "Google": execute_google_api,
    "Mistral": execute_mistral_api,
    "Azure OpenAI": execute_azure_openai_api,
    "LMStudio": execute_lmstudio_api,
    "Ollama": execute_ollama_api,
    "OpenRouter": execute_openrouter_api,
}

async def call_api_with_retry(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str, cancelled: bool) -> str:
    retries = SETTINGS.get("API_CALL_MAX_RETRIES", 3)
    interval_seconds = SETTINGS.get("API_CALL_INTERVAL", 5)
    if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
        raise ValueError("API_CALL_MAX_RETRIES must be a nonnegative integer")
    if not isinstance(interval_seconds, (int, float)) or not math.isfinite(interval_seconds) or interval_seconds < 0:
        raise ValueError("API_CALL_INTERVAL must be finite and nonnegative")
    api_call_function = API_CALL_FUNCTIONS.get(provider_config["name"])
    if not api_call_function:
        raise ValueError(f"Unsupported provider: {provider_config['name']}")
    for attempt in range(retries + 1):
        if cancelled:
            raise asyncio.CancelledError("Processing cancelled before API attempt")
        try:
            response = await api_call_function(provider_config, model_name, prompt, content)
            if cancelled:
                raise asyncio.CancelledError("Processing cancelled after API response")
            return response
        except httpx.HTTPStatusError as error:
            if error.response.status_code not in (408, 425, 429, 500, 502, 503, 504) or attempt == retries:
                raise
            logger.warning("Provider attempt %d failed with HTTP %d", attempt + 1, error.response.status_code)
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as error:
            if attempt == retries:
                raise
            logger.warning("Provider attempt %d failed with %s", attempt + 1, type(error).__name__)
        # Task cancellation propagates through this await; configuration and parser
        # failures are not transient and never cause repeated paid requests.
        await cancellable_delay(interval_seconds * 1000, cancelled)

async def call_llm_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str, cancelled: bool = False) -> str:
    if cancelled:
        raise asyncio.CancelledError("Processing cancelled before API call")
    if SETTINGS.get("ENABLE_STABLE_API_CALL", False):
        return await call_api_with_retry(provider_config, model_name, prompt, content, cancelled)
    api_call_function = API_CALL_FUNCTIONS.get(provider_config["name"])
    if not api_call_function:
        raise ValueError(f"Unsupported provider: {provider_config['name']}")
    response = await api_call_function(provider_config, model_name, prompt, content)
    if cancelled:
        raise asyncio.CancelledError("Processing cancelled after API response")
    return response

# --- Duplicate Handling (from fileUtils.ts) ---
def find_duplicates(content: str) -> set[str]:
    duplicates = set()
    seen_words = set()
    lines = content.split('\n')

    for line in lines:
        words = re.findall(r'\b\w+\b', line)
        for word in words:
            normalized = word.lower().replace("'s", '')
            if len(normalized) > 2:
                if normalized in seen_words:
                    duplicates.add(normalized)
                seen_words.add(normalized)
    return duplicates

def get_duplicate_words(content: str) -> List[str]:
    return sorted(find_duplicates(content))

async def handle_duplicates(content: str):
    if not SETTINGS.get("ENABLE_DUPLICATE_DETECTION", True):
        logger.info("Duplicate detection is disabled in settings.")
        return
    potential_issues = set()
    duplicate_words = find_duplicates(content)
    for word in duplicate_words:
        potential_issues.add(f'Duplicate word: "{word}"')

    if potential_issues:
        logger.info(f"Found {len(potential_issues)} potential duplicate/consistency issues in processed content.")
        for issue in potential_issues:
            logger.info(issue)

# --- Search Functions (from searchUtils.ts) ---
async def search_duckduckgo(query: str) -> List[Dict[str, str]]:
    max_results = SETTINGS.get("DDG_MAX_RESULTS", 5)
    encoded_query = quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    results = []

    logger.info(f"Querying DuckDuckGo HTML endpoint: {url}")
    try:
        async with httpx.AsyncClient(timeout=SETTINGS.get("DDG_FETCH_TIMEOUT", 15)) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            })
            response.raise_for_status()

        html_content = response.text
        logger.info(f"Received HTML response from DuckDuckGo ({len(html_content)} bytes). Parsing...")

        parser = LexborHTMLParser(html_content)
        candidate_nodes = parser.css('.result--html') or parser.css('.result__body') or parser.css('.result')
        for node in candidate_nodes:
            if len(results) >= max_results:
                break

            link_node = node.css_first('.result__a')
            snippet_node = node.css_first('.result__snippet')
            if not link_node:
                continue

            link = link_node.attributes.get('href')
            title = link_node.text(strip=True)
            snippet = snippet_node.text(strip=True) if snippet_node else ""

            if link and title:
                if link.startswith('/l/?uddg='):
                    parsed_url = urlparse(link)
                    decoded_link = parse_qs(parsed_url.query).get('uddg', [None])[0]
                    if decoded_link:
                        link = decoded_link
                    else:
                        logger.info(f"Warning: Could not decode DDG redirect URL: {link}")
                        link = f"https://duckduckgo.com{link}"
                elif not link.startswith('http'):
                    link = f"https://duckduckgo.com{link}"

                results.append({"title": title, "url": link, "content": snippet or title})
            else:
                logger.info(f"Warning: Skipping partially parsed result (Title: {bool(title)}, Link: {bool(link)})")

        # Fallback: extract direct anchors when container selectors change.
        if not results:
            for link_node in parser.css('a.result__a'):
                if len(results) >= max_results:
                    break
                link = link_node.attributes.get('href')
                title = link_node.text(strip=True)
                if not link or not title:
                    continue
                if link.startswith('/l/?uddg='):
                    parsed_url = urlparse(link)
                    decoded_link = parse_qs(parsed_url.query).get('uddg', [None])[0]
                    link = decoded_link or link
                elif not link.startswith('http'):
                    link = f"https://duckduckgo.com{link}"
                results.append({"title": title, "url": link, "content": title})

        if not results:
            logger.info("Warning: Could not parse any valid results from DuckDuckGo HTML.")
        else:
            logger.info(f"Successfully parsed {len(results)} results from DuckDuckGo.")
        return results

    except Exception as e:
        logger.info(f"Automated DuckDuckGo search failed. Error: {e}. Consider using Tavily.")
        return []

async def fetch_content_from_url(url: str) -> str:
    logger.info(f"Fetching content from: {url}")
    try:
        async with httpx.AsyncClient(timeout=SETTINGS.get("DDG_FETCH_TIMEOUT", 15)) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })
            response.raise_for_status()

        content_type = response.headers.get('content-type', '')
        if 'text/html' not in content_type:
            logger.info(f"Skipping non-HTML content ({content_type}) from: {url}")
            return f"[Content skipped: Not HTML - {content_type}]"

        parser = LexborHTMLParser(response.text)
        if parser.body is None:
            return "[Content skipped: No body tag found]"
        for script in parser.css('script'): script.decompose()
        for style in parser.css('style'): style.decompose()

        text = parser.body.text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text).strip()

        max_length = 15000
        if len(text) > max_length:
            text = text[:max_length] + "... [content truncated]"
            logger.info(f"Truncated content from: {url}")

        logger.info(f"Successfully fetched and extracted text from: {url}")
        return text

    except Exception as e:
        logger.info(f"Error fetching content from {url}: {e}")
        return f"[Content skipped: Error fetching - {e}]"

async def _perform_research(topic: str, cancelled: bool) -> Optional[str]:
    logger.info(f'Entering _perform_research for topic: "{topic}"')
    search_query = f"{topic} wiki"
    combined_content = ''
    search_source = ''
    search_results = []

    try:
        if SETTINGS.get("SEARCH_PROVIDER", "tavily") == "tavily":
            search_source = 'Tavily'
            logger.info("Selected search provider: Tavily.")
            if not SETTINGS.get("TAVILY_API_KEY"): raise ValueError('Tavily API key is not configured.')
            if cancelled: raise Exception("Processing cancelled by user before Tavily search.")

            tavily_url = 'https://api.tavily.com/search'
            logger.info(f'Searching Tavily for: "{search_query}"')
            
            tavily_request_body = {
                "api_key": SETTINGS["TAVILY_API_KEY"],
                "query": search_query,
                "search_depth": SETTINGS.get("TAVILY_SEARCH_DEPTH", "basic"),
                "include_answer": False,
                "include_raw_content": False,
                "max_results": SETTINGS.get("TAVILY_MAX_RESULTS", 5)
            }
            
            async with httpx.AsyncClient(timeout=SETTINGS.get("DDG_FETCH_TIMEOUT", 15)) as client:
                response = await client.post(tavily_url, json=tavily_request_body)
                response.raise_for_status()
            
            if cancelled: raise Exception("Processing cancelled by user during Tavily search.")
            tavily_data = response.json()
            if not tavily_data.get("results"): 
                logger.info('Tavily returned no results.')
                return None
            search_results = tavily_data["results"]
            logger.info(f"Fetched {len(search_results)} results from Tavily.")

        else:
            search_source = 'DuckDuckGo'
            logger.info("Selected search provider: DuckDuckGo.")
            if cancelled: raise Exception("Processing cancelled by user before DuckDuckGo search.")
            logger.info(f'Searching DuckDuckGo for: "{search_query}"')
            search_results = await search_duckduckgo(search_query)
            if cancelled: raise Exception("Processing cancelled by user during DuckDuckGo search.")
            if not search_results: 
                logger.info('DuckDuckGo search failed or returned no results.')
                return None
        
        fetched_contents = []
        if search_source == 'DuckDuckGo':
            logger.info(f"Fetching content for top {len(search_results)} DuckDuckGo results...")
            fetch_promises = [fetch_content_from_url(result["url"]) for result in search_results]
            fetched_contents = await asyncio.gather(*fetch_promises)
            if cancelled: raise Exception("Processing cancelled by user during DuckDuckGo content fetching.")
            logger.info(f"Finished fetching content for DuckDuckGo results.")
        else:
            logger.info("Using snippets directly from Tavily results.")
            fetched_contents = [result["content"] for result in search_results]

        if cancelled: raise Exception("Processing cancelled by user before combining content.")

        if fetched_contents:
            logger.info(f"Combining {len(fetched_contents)} fetched/snippet contents.")
            combined_content = f'Research context for "{search_query}" (via {search_source}):\n\n'
            for i, result in enumerate(search_results):
                combined_content += f"Result {i + 1}:\n"
                combined_content += f"Title: {result['title']}\n"
                combined_content += f"URL: {result['url']}\n"
                combined_content += f"{search_source if search_source == 'Tavily' else 'Content'}: {fetched_contents[i] if fetched_contents[i] else '[No content available]'}\n\n"

            estimated_tokens_count = estimate_tokens(combined_content)
            max_tokens = SETTINGS.get("MAX_RESEARCH_CONTENT_TOKENS", 3000)
            logger.info(f"Estimated research context tokens: {estimated_tokens_count}. Limit: {max_tokens}")
            if estimated_tokens_count > max_tokens:
                max_chars = max_tokens * 4
                combined_content = combined_content[:max_chars] + "\n\n[...research context truncated due to token limit]"
                logger.info(f"Truncated research context to ~{max_tokens} tokens.")
            return combined_content.strip()
        else:
            logger.info('No content could be obtained from search results.')
            return None

    except Exception as e:
        logger.info(f'Error in _perform_research catch block for "{topic}": {e}')
        return None

# --- Main Processing Function ---
async def process_content(content: str, cancelled: bool = False) -> str:
    chunks = split_content(content)
    processed_chunks = []

    provider_config = get_provider_for_task("addLinks")
    if not provider_config:
        raise ValueError(f"Active provider not found in settings.")
    model_name = get_model_for_task("addLinks", provider_config)

    for chunk in chunks:
        llm_response = await call_llm_api(provider_config, model_name, get_llm_processing_prompt(), chunk, cancelled)
        processed_chunks.append(unwrap_markdown_response(llm_response))

    processed_content = "\n\n".join(processed_chunks).replace("\n\n\n", "\n\n").strip()

    final_content = cleanup_latex_delimiters(processed_content)
    final_content = refine_mermaid_blocks(final_content)

    lines = final_content.split('\n')
    if lines and lines[0].strip() == '\\boxed{':
        lines.pop(0)
        if lines and lines[-1].strip() == '}':
            lines.pop()
        final_content = '\n'.join(lines)

    # Provider envelopes have already been removed per chunk. Inner code fences
    # belong to the document, including when the legacy removal setting is enabled.

    await handle_duplicates(final_content)

    return final_content

async def generate_content_for_title(title: str, cancelled: bool = False) -> str:
    logger.info(f"Starting content generation for: {title}")
    provider_config = get_provider_for_task("generateTitle")
    if not provider_config: raise ValueError("No valid LLM provider configured for \"Generate from Title\" task.")
    model_name = get_model_for_task("generateTitle", provider_config)

    research_context = ''
    if SETTINGS.get("ENABLE_RESEARCH_IN_GENERATE_CONTENT", False):
        if cancelled: raise Exception("Processing cancelled by user before research.")
        logger.info(f'Research enabled for "{title}". Performing web search...')
        try:
            context = await _perform_research(title, cancelled)
            if cancelled: raise Exception("Processing cancelled by user during research.")
            if context:
                research_context = context
                logger.info(f'Research context obtained for "{title}".')
            else:
                logger.info(f'Warning: Research for "{title}" returned no results or failed.')
        except Exception as e:
            if "cancelled by user" in str(e): raise e
            logger.info(f'Error during research for "{title}": {e}. Proceeding without web context.')
    else:
        logger.info("Research disabled for \"Generate from Title\".")
    if cancelled: raise Exception("Processing cancelled by user before generation prompt construction.")

    research_context_section = f"\n\nUse the following research context to inform the documentation:\n\n{research_context}\n\n" if research_context else ""
    
    custom_prompt_template = SETTINGS.get("CUSTOM_PROMPT_GENERATE_TITLE")
    if not custom_prompt_template:
        raise ValueError("Custom prompt for 'Generate from Title' is not configured.")
    generation_prompt = format_prompt(
        custom_prompt_template,
        {
            "TITLE": title,
            "RESEARCH_CONTEXT_SECTION": research_context_section,
        }
    )

    target_language_name = next((lang["name"] for lang in SETTINGS.get("AVAILABLE_LANGUAGES", []) if lang["code"] == SETTINGS.get("LANGUAGE", "en")), SETTINGS.get("LANGUAGE", "en"))
    if SETTINGS.get("LANGUAGE", "en") != "en":
        generation_prompt += f'\n\nIMPORTANT: Process the request and perform all reasoning in English. However, the final output MUST be written in {target_language_name}.In mermaid diagrams, it is necessary to translate into {target_language_name} while retaining the English.'

    if cancelled: raise Exception("Processing cancelled by user before API call.")
    logger.info(f"Calling {provider_config['name']} to generate content...")

    generated_content = await call_llm_api(provider_config, model_name, generation_prompt, "", cancelled)

    if cancelled: raise Exception("Processing cancelled by user after API call.")
    logger.info(f"Content received from {provider_config['name']}.")

    final_content = cleanup_latex_delimiters(generated_content)
    if cancelled: raise Exception("Processing cancelled by user during post-processing.")
    final_content = refine_mermaid_blocks(final_content)
    logger.info("Mermaid/LaTeX cleanup applied.")

    if cancelled: raise Exception("Processing cancelled by user after post-processing.")

    lines = final_content.split('\n')
    if lines and lines[0].strip() == '\\boxed{':
        lines.pop(0)
        if lines and lines[-1].strip() == '}':
            lines.pop()
        final_content = '\n'.join(lines)

    if cancelled: raise Exception("Processing cancelled by user before saving.")

    return final_content

async def research_and_summarize(topic: str, cancelled: bool = False) -> str:
    logger.info(f'Starting research for topic: "{topic}"')

    if cancelled: raise Exception("Processing cancelled by user before research.")
    research_context = await _perform_research(topic, cancelled)

    if cancelled: raise Exception("Processing cancelled by user during research.")

    if not research_context:
        raise ValueError(f'Research for "{topic}" failed or returned no results. Summary not generated.')
    logger.info(f'_perform_research returned context for "{topic}" (length: {len(research_context)}).')

    provider_config = get_provider_for_task("research")
    if not provider_config: raise ValueError("No valid LLM provider configured for the \"Research & Summarize\" task.")
    model_name = get_model_for_task("research", provider_config)
    logger.info(f'Using provider "{provider_config["name"]}" and model "{model_name}" for summarization.')

    if cancelled: raise Exception("Processing cancelled by user before summarization.")

    summary_prompt_template = SETTINGS.get("CUSTOM_PROMPT_RESEARCH_SUMMARIZE")
    if not summary_prompt_template:
        raise ValueError("Custom prompt for 'Research & Summarize' is not configured.")
    summary_prompt = summary_prompt_template.format(
        TOPIC=topic,
        SEARCH_RESULTS_CONTEXT=research_context,
        LANGUAGE=resolve_language_display_name(SETTINGS.get("LANGUAGE", "en"))
    )

    summary = await call_llm_api(provider_config, model_name, summary_prompt, "", cancelled)

    if cancelled: raise Exception("Processing cancelled by user after summarization.")

    logger.info(f"Generated summary using {provider_config['name']}.")

    final_summary = cleanup_latex_delimiters(summary)
    if cancelled: raise Exception("Processing cancelled by user during post-processing.")
    final_summary = refine_mermaid_blocks(final_summary)
    logger.info("Mermaid/LaTeX cleanup applied to summary.")

    if cancelled: raise Exception("Processing cancelled by user after post-processing.")

    summary_to_append = final_summary.strip()
    lines = summary_to_append.split('\n')
    if lines and lines[0].strip() == '\\boxed{':
        lines.pop(0)
        if lines and lines[-1].strip() == '}':
            lines.pop()
        summary_to_append = '\n'.join(lines)

    if cancelled: raise Exception("Processing cancelled by user before appending summary.")

    search_source = SETTINGS.get("SEARCH_PROVIDER", "tavily")
    summary_header = f"\n\n## Research Summary (via {search_source.capitalize()}): {topic}\n\n"

    return summary_header + summary_to_append

async def execute_custom_prompt(prompt: str, content: str, cancelled: bool = False) -> str:
    logger.info(f"Executing custom prompt...")
    provider_config = get_provider_for_task("addLinks") # Use default provider for custom tasks
    if not provider_config:
        raise ValueError(f"Active provider not found in settings.")
    model_name = get_model_for_task("addLinks", provider_config)

    llm_response = await call_llm_api(provider_config, model_name, prompt, content, cancelled)

    return llm_response

async def translate_content(content: str, target_language: str = "en", cancelled: bool = False) -> str:
    if not content.strip():
        raise ValueError("Content is empty. Cannot translate.")

    provider_config = get_provider_for_task("translate")
    if not provider_config:
        raise ValueError("No valid LLM provider configured for the \"Translate\" task.")
    model_name = get_model_for_task("translate", provider_config)

    prompt_template = SETTINGS.get("CUSTOM_PROMPT_TRANSLATE")
    if not prompt_template:
        raise ValueError("Custom prompt for 'Translate' is not configured.")

    language_name = resolve_language_display_name(target_language)
    chunks = split_content(content)
    translated_chunks: List[str] = []
    for chunk in chunks:
        if cancelled:
            raise Exception("Processing cancelled by user during translation.")
        prompt = format_prompt(prompt_template, {"LANGUAGE": language_name, "TEXT": chunk})
        translated_chunk = await call_llm_api(provider_config, model_name, prompt, "", cancelled)
        translated_chunks.append(translated_chunk.strip())

    combined = "\n\n".join(translated_chunks)
    return apply_standard_post_processing(combined, remove_markdown_fence=True)

async def summarize_as_mermaid(content: str, target_language: str = "en", cancelled: bool = False) -> str:
    if not content.strip():
        raise ValueError("Content is empty. Cannot summarize as Mermaid.")

    provider_config = get_provider_for_task("summarizeToMermaid")
    if not provider_config:
        raise ValueError("No valid LLM provider configured for the \"Summarize as Mermaid\" task.")
    model_name = get_model_for_task("summarizeToMermaid", provider_config)

    prompt_template = SETTINGS.get("CUSTOM_PROMPT_SUMMARIZE_TO_MERMAID")
    if not prompt_template:
        raise ValueError("Custom prompt for 'Summarize as Mermaid' is not configured.")

    language_name = resolve_language_display_name(target_language)
    prompt = format_prompt(prompt_template, {"LANGUAGE": language_name, "TEXT": content})
    mermaid = await call_llm_api(provider_config, model_name, prompt, "", cancelled)
    cleaned = apply_standard_post_processing(mermaid)
    return ensure_mermaid_code_block(cleaned, fallback_header="mindmap")

async def generate_diagram(
    content: str,
    diagram_intent: str = "auto",
    target_language: str = "en",
    compatibility_mode: str = "canonical",
    cancelled: bool = False
) -> str:
    if not content.strip():
        raise ValueError("Content is empty. Cannot generate diagram.")

    provider_config = get_provider_for_task("diagramGenerate")
    if not provider_config:
        raise ValueError("No valid LLM provider configured for the \"Generate diagram\" task.")
    model_name = get_model_for_task("diagramGenerate", provider_config)

    language_name = resolve_language_display_name(target_language)
    if compatibility_mode == "legacy-mermaid":
        prompt_template = SETTINGS.get("CUSTOM_PROMPT_SUMMARIZE_TO_MERMAID")
        if not prompt_template:
            raise ValueError("Custom prompt for legacy Mermaid generation is not configured.")
        prompt = format_prompt(prompt_template, {"LANGUAGE": language_name, "TEXT": content})
        fallback_header = "mindmap"
    else:
        prompt_template = SETTINGS.get("CUSTOM_PROMPT_GENERATE_DIAGRAM")
        if not prompt_template:
            raise ValueError("Custom prompt for diagram generation is not configured.")
        prompt = format_prompt(
            prompt_template,
            {
                "DIAGRAM_INTENT": diagram_intent or "auto",
                "LANGUAGE": language_name,
                "TEXT": content,
            }
        )
        fallback_header = "graph TD"

    generated = await call_llm_api(provider_config, model_name, prompt, "", cancelled)
    cleaned = apply_standard_post_processing(generated)
    return ensure_mermaid_code_block(cleaned, fallback_header=fallback_header)

def parse_concepts_from_response(response_text: str) -> List[str]:
    concepts: List[str] = []
    seen = set()
    for raw_line in response_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^CONCEPT:\s*(.+?)\s*$", line, re.IGNORECASE)
        if not match:
            continue
        concept = match.group(1).strip()
        if not concept:
            continue
        normalized = concept.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        concepts.append(concept)
    return concepts

async def extract_concepts(content: str, cancelled: bool = False) -> List[str]:
    if not content.strip():
        raise ValueError("Content is empty. Cannot extract concepts.")

    provider_config = get_provider_for_task("extractConcepts")
    if not provider_config:
        raise ValueError("No valid LLM provider configured for the \"Extract concepts\" task.")
    model_name = get_model_for_task("extractConcepts", provider_config)

    prompt_template = SETTINGS.get("CUSTOM_PROMPT_EXTRACT_CONCEPTS")
    if not prompt_template:
        raise ValueError("Custom prompt for 'Extract concepts' is not configured.")

    chunks = split_content(content)
    parsed_concepts: List[str] = []
    seen = set()
    for chunk in chunks:
        if cancelled:
            raise Exception("Processing cancelled by user during concept extraction.")
        prompt = format_prompt(prompt_template, {"REFERENCE_CONTENT": chunk})
        response = await call_llm_api(provider_config, model_name, prompt, "", cancelled)
        for concept in parse_concepts_from_response(response):
            normalized = concept.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            parsed_concepts.append(concept)
    return parsed_concepts

async def extract_original_text(reference_content: str, user_input: str, cancelled: bool = False) -> str:
    if not reference_content.strip():
        raise ValueError("Reference content is empty.")
    if not user_input.strip():
        raise ValueError("User input is empty.")

    provider_config = get_provider_for_task("extractOriginalText")
    if not provider_config:
        raise ValueError("No valid LLM provider configured for the \"Extract original text\" task.")
    model_name = get_model_for_task("extractOriginalText", provider_config)

    prompt_template = SETTINGS.get("CUSTOM_PROMPT_EXTRACT_ORIGINAL_TEXT")
    if not prompt_template:
        raise ValueError("Custom prompt for 'Extract original text' is not configured.")

    prompt = format_prompt(
        prompt_template,
        {"REFERENCE_CONTENT": reference_content, "USER_INPUT": user_input}
    )
    extracted = await call_llm_api(provider_config, model_name, prompt, "", cancelled)
    return apply_standard_post_processing(extracted)

# --- File Utilities ---

async def handle_file_rename(old_path: str, new_path: str):
    old_name = os.path.splitext(os.path.basename(old_path))[0]
    new_name = os.path.splitext(os.path.basename(new_path))[0]

    if not old_name or not new_name or old_name == new_name:
        return

    logger.info(f"Updating links for renamed file: {new_name}")

    link_regex = re.compile(r'\[\[{}\]\]'.format(re.escape(old_name)))
    updated_count = 0
    errors = []

    for root, _, files in os.walk(SETTINGS["VAULT_ROOT"]):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                if file_path == new_path: continue
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if re.search(link_regex, content):
                        updated_content = re.sub(link_regex, f"[[{new_name}]]", content)
                        if content != updated_content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(updated_content)
                            updated_count += 1
                except Exception as e:
                    error_msg = f"Error updating links in {file_path} for rename: {e}"
                    logger.info(error_msg)
                    errors.append(error_msg)
    
    logger.info(f"Updated links to \"{new_name}\" in {updated_count} files.")
    if errors:
        logger.info(f"Encountered {len(errors)} errors while updating links.")

async def handle_file_delete(path: str):
    file_name = os.path.splitext(os.path.basename(path))[0]
    if not file_name:
        return

    logger.info(f"Removing links for deleted file: {file_name}")

    link_regex = re.compile(r'\[\[{}\]\]'.format(re.escape(file_name)), re.IGNORECASE)
    updated_count = 0
    errors = []

    for root, _, files in os.walk(SETTINGS["VAULT_ROOT"]):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    updated_content = re.sub(link_regex, '', content)
                    updated_content = re.sub(r'^[ \t]*[-*+]\s*$', '', updated_content, flags=re.MULTILINE)
                    updated_content = re.sub(r'\n{3,}', '\n\n', updated_content).strip()

                    if content != updated_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(updated_content)
                        updated_count += 1
                except Exception as e:
                    error_msg = f"Error removing links from {file_path} for delete: {e}"
                    logger.info(error_msg)
                    errors.append(error_msg)

    logger.info(f"Removed links to \"{file_name}\" from {updated_count} files.")
    if errors:
        logger.info(f"Encountered {len(errors)} errors while removing links.")

async def batch_fix_mermaid_syntax_in_folder(folder_path: str):
    if not os.path.isdir(folder_path):
        raise ValueError(f"Selected path is not a valid folder: {folder_path}")

    modified_count = 0
    errors = []

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                try:
                    if os.path.islink(file_path):
                        raise ValueError("Symbolic links are not processed")
                    with open(file_path, 'r', encoding='utf-8', newline='') as f:
                        original_content = f.read()
                    
                    processed_content = cleanup_latex_delimiters(original_content)
                    processed_content = refine_mermaid_blocks(processed_content)

                    if processed_content != original_content:
                        write_changed_markdown(file_path, original_content, processed_content)
                        modified_count += 1
                        logger.info(f"Fixed syntax in: {file_path}")
                except Exception as e:
                    error_msg = f"Error fixing syntax in {file_path}: {e}"
                    logger.info(error_msg)
                    errors.append({"file": file_path, "message": str(e)})
    
    return {"errors": errors, "modified_count": modified_count}


def write_changed_markdown(file_path: str, original: str, updated: str) -> None:
    """Stage complete output beside the source, then replace it after a fresh-read check."""
    source_mode = os.stat(file_path).st_mode
    if not source_mode & 0o222:
        raise PermissionError("Source is read-only; syntax repair was not written")
    candidate = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='', dir=os.path.dirname(file_path), prefix='.notemd-', suffix='.tmp', delete=False) as output:
            candidate = output.name
            output.write(updated)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(candidate, source_mode)
        with open(file_path, 'r', encoding='utf-8', newline='') as source:
            if source.read() != original:
                raise ValueError("Source changed during syntax repair")
        os.replace(candidate, file_path)
        candidate = None
    finally:
        if candidate is not None:
            os.unlink(candidate)
