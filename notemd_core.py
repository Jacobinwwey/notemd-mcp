# notemd_core.py

import re
import httpx
import json
import time
import os
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, quote
from selectolax.parser import HTMLParser

# Placeholder for settings, will be imported from config.py
SETTINGS = {}

def set_settings(settings_dict):
    global SETTINGS
    SETTINGS = settings_dict

# --- Utility Functions (from utils.ts) ---
def cancellable_delay(ms: int, cancelled: bool) -> None:
    if cancelled:
        raise Exception("Processing cancelled")
    time.sleep(ms / 1000.0)
    if cancelled:
        raise Exception("Processing cancelled")

def estimate_tokens(text: str) -> int:
    if not text: return 0
    return len(text) // 4

def get_provider_for_task(task_type: str) -> Optional[Dict[str, Any]]:
    provider_name = SETTINGS.get("ACTIVE_PROVIDER", "DeepSeek")
    if SETTINGS.get("USE_MULTI_MODEL_SETTINGS", False):
        if task_type == "addLinks":
            provider_name = SETTINGS.get("ADD_LINKS_PROVIDER", provider_name)
        elif task_type == "research":
            provider_name = SETTINGS.get("RESEARCH_PROVIDER", provider_name)
        elif task_type == "generateTitle":
            provider_name = SETTINGS.get("GENERATE_TITLE_PROVIDER", provider_name)

    for p in SETTINGS.get("DEFAULT_PROVIDERS", []) :
        if p["name"] == provider_name:
            return p
    return None

def get_model_for_task(task_type: str, provider_config: Dict[str, Any]) -> str:
    model_name = provider_config.get("model")
    if SETTINGS.get("USE_MULTI_MODEL_SETTINGS", False):
        if task_type == "addLinks":
            model_name = SETTINGS.get("ADD_LINKS_MODEL") or model_name
        elif task_type == "research":
            model_name = SETTINGS.get("RESEARCH_MODEL") or model_name
        elif task_type == "generateTitle":
            model_name = SETTINGS.get("GENERATE_TITLE_MODEL") or model_name
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
    url = f"{provider_config['baseUrl']}/models/{model_name}:generateContent?key={provider_config['apiKey']}"
    headers = {"Content-Type": "application/json"}
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
    last_error = None
    max_attempts = SETTINGS.get("API_CALL_MAX_RETRIES", 3) + 1
    interval_seconds = SETTINGS.get("API_CALL_INTERVAL", 5)

    for attempt in range(1, max_attempts + 1):
        if cancelled: raise Exception("Processing cancelled by user before API attempt.")
        try:
            api_call_function = API_CALL_FUNCTIONS.get(provider_config["name"])
            if not api_call_function: raise ValueError(f"Unsupported provider: {provider_config['name']}")
            return await api_call_function(provider_config, model_name, prompt, content)
        except httpx.HTTPStatusError as e:
            print(f"API Call: Attempt {attempt} failed with HTTP status {e.response.status_code}: {e.response.text}")
            last_error = e
            if e.response.status_code in [400, 401, 403, 404]:
                raise e
        except httpx.RequestError as e:
            print(f"API Call: Attempt {attempt} failed with request error: {e}")
            last_error = e
        except Exception as e:
            print(f"API Call: Attempt {attempt} failed with unexpected error: {e}")
            last_error = e

        if cancelled: raise Exception("Processing cancelled by user during API retry sequence.")

        if attempt < max_attempts:
            print(f"Waiting {interval_seconds} seconds before retry {attempt + 1}...")
            cancellable_delay(interval_seconds * 1000, cancelled)

    raise Exception(f"API call failed after {max_attempts} attempts. Last error: {last_error}")

async def call_llm_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str, cancelled: bool = False) -> str:
    if SETTINGS.get("ENABLE_STABLE_API_CALL", False):
        return await call_api_with_retry(provider_config, model_name, prompt, content, cancelled)
    else:
        api_call_function = API_CALL_FUNCTIONS.get(provider_config["name"])
        if not api_call_function: raise ValueError(f"Unsupported provider: {provider_config['name']}")
        return await api_call_function(provider_config, model_name, prompt, content)

# --- Mermaid and LaTeX Processing (from mermaidProcessor.ts) ---
def refine_mermaid_blocks(content: str) -> str:
    lines = content.split('\n')
    result_lines = []
    in_mermaid = False
    current_block_lines = []
    last_arrow_index_in_block = -1

    for line in lines:
        stripped = line.strip()
        mermaid_start_regex = re.compile(r'^```\s*\(?\s*mermaid\s*\)?')

        if mermaid_start_regex.search(stripped):
            line = mermaid_start_regex.sub('```mermaid', line)
            if in_mermaid:
                if last_arrow_index_in_block != -1:
                    if (last_arrow_index_in_block + 1 >= len(current_block_lines) or\
                            current_block_lines[last_arrow_index_in_block + 1].strip() != '```'):
                        current_block_lines.insert(last_arrow_index_in_block + 1, '```')
                elif current_block_lines:
                    if current_block_lines[0].strip().startswith('```mermaid') and \
                       current_block_lines[-1].strip() != '```':
                        if len(current_block_lines) == 1 or current_block_lines[1].strip() != '```':
                            current_block_lines.insert(1, '```')
            result_lines.extend(current_block_lines)
            in_mermaid = True
            current_block_lines = [line]
            last_arrow_index_in_block = -1
        elif in_mermaid:
            if "subgraph" not in line:
                line = line.replace('"', '')

            current_block_lines.append(line)
            if "-->" in line:
                last_arrow_index_in_block = len(current_block_lines) - 1
            if stripped == '```':
                result_lines.extend(current_block_lines)
                in_mermaid = False
                current_block_lines = []
                last_arrow_index_in_block = -1
        else:
            result_lines.append(line)

    if in_mermaid:
        if last_arrow_index_in_block != -1:
            if (last_arrow_index_in_block + 1 >= len(current_block_lines) or\
                    current_block_lines[last_arrow_index_in_block + 1].strip() != '```'):
                current_block_lines.insert(last_arrow_index_in_block + 1, '```')
        elif current_block_lines:
            if current_block_lines[0].strip().startswith('```mermaid') and \
               current_block_lines[-1].strip() != '```':
                if len(current_block_lines) == 1 or current_block_lines[1].strip() != '```':
                    current_block_lines.insert(1, '```')
                elif current_block_lines[-1].strip() != '```':
                    current_block_lines.append('```')
        elif current_block_lines[-1].strip() != '```':
            current_block_lines.append('```')
        result_lines.extend(current_block_lines)

    return '\n'.join(result_lines)

def cleanup_latex_delimiters(content: str) -> str:
    processed = content
    processed = re.sub(r'\\\$', '___TEMP_DOLLAR_ESCAPE___', processed)
    processed = re.sub(r'\$\s*([^$]*?)\s*\$', lambda m: m.group(0) if m.group(0).startswith('$$') and m.group(0).endswith('$$') else f"${m.group(1).strip()}$", processed)
    processed = re.sub(r'___TEMP_DOLLAR_ESCAPE___', '$', processed)
    return processed

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

async def handle_duplicates(content: str):
    if not SETTINGS.get("ENABLE_DUPLICATE_DETECTION", True):
        print("Duplicate detection is disabled in settings.")
        return
    potential_issues = set()
    duplicate_words = find_duplicates(content)
    for word in duplicate_words:
        potential_issues.add(f'Duplicate word: "{word}"')

    if potential_issues:
        print(f"Found {len(potential_issues)} potential duplicate/consistency issues in processed content.")
        for issue in potential_issues:
            print(issue)

# --- Search Functions (from searchUtils.ts) ---
async def search_duckduckgo(query: str) -> List[Dict[str, str]]:
    max_results = SETTINGS.get("DDG_MAX_RESULTS", 5)
    encoded_query = quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    results = []

    print(f"Querying DuckDuckGo HTML endpoint: {url}")
    try:
        async with httpx.AsyncClient(timeout=SETTINGS.get("DDG_FETCH_TIMEOUT", 15)) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            })
            response.raise_for_status()

        html_content = response.text
        print(f"Received HTML response from DuckDuckGo ({len(html_content)} bytes). Parsing...")

        parser = HTMLParser(html_content)
        for node in parser.css('.result--html'):
            if len(results) >= max_results: break

            link_node = node.css_first('.result__a')
            snippet_node = node.css_first('.result__snippet')

            if link_node and snippet_node:
                link = link_node.attributes.get('href')
                title = link_node.text(strip=True)
                snippet = snippet_node.text(strip=True)

                if link and title and snippet:
                    if link.startswith('/l/?uddg='):
                        parsed_url = urlparse(link)
                        decoded_link = parse_qs(parsed_url.query).get('uddg', [None])[0]
                        if decoded_link:
                            link = decoded_link
                        else:
                            print(f"Warning: Could not decode DDG redirect URL: {link}")
                            link = f"https://duckduckgo.com{link}"
                    elif not link.startswith('http'):
                        link = f"https://duckduckgo.com{link}"

                    results.append({"title": title, "url": link, "content": snippet})
                else:
                    print(f"Warning: Skipping partially parsed result (Title: {bool(title)}, Link: {bool(link)}, Snippet: {bool(snippet)})")

        if not results:
            print("Warning: Could not parse any valid results from DuckDuckGo HTML.")
        else:
            print(f"Successfully parsed {len(results)} results from DuckDuckGo.")
        return results

    except Exception as e:
        print(f"Automated DuckDuckGo search failed. Error: {e}. Consider using Tavily.")
        return []

async def fetch_content_from_url(url: str) -> str:
    print(f"Fetching content from: {url}")
    try:
        async with httpx.AsyncClient(timeout=SETTINGS.get("DDG_FETCH_TIMEOUT", 15)) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })
            response.raise_for_status()

        content_type = response.headers.get('content-type', '')
        if 'text/html' not in content_type:
            print(f"Skipping non-HTML content ({content_type}) from: {url}")
            return f"[Content skipped: Not HTML - {content_type}]"

        parser = HTMLParser(response.text)
        if parser.body is None:
            return "[Content skipped: No body tag found]"
        for script in parser.css('script'): script.decompose()
        for style in parser.css('style'): style.decompose()

        text = parser.body.text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text).strip()

        max_length = 15000
        if len(text) > max_length:
            text = text[:max_length] + "... [content truncated]"
            print(f"Truncated content from: {url}")

        print(f"Successfully fetched and extracted text from: {url}")
        return text

    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return f"[Content skipped: Error fetching - {e}]"

async def _perform_research(topic: str, cancelled: bool) -> Optional[str]:
    print(f'Entering _perform_research for topic: "{topic}"')
    search_query = f"{topic} wiki"
    combined_content = ''
    search_source = ''
    search_results = []

    try:
        if SETTINGS.get("SEARCH_PROVIDER", "tavily") == "tavily":
            search_source = 'Tavily'
            print("Selected search provider: Tavily.")
            if not SETTINGS.get("TAVILY_API_KEY"): raise ValueError('Tavily API key is not configured.')
            if cancelled: raise Exception("Processing cancelled by user before Tavily search.")

            tavily_url = 'https://api.tavily.com/search'
            print(f'Searching Tavily for: "{search_query}"')
            
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
                print('Tavily returned no results.')
                return None
            search_results = tavily_data["results"]
            print(f"Fetched {len(search_results)} results from Tavily.")

        else:
            search_source = 'DuckDuckGo'
            print("Selected search provider: DuckDuckGo.")
            if cancelled: raise Exception("Processing cancelled by user before DuckDuckGo search.")
            print(f'Searching DuckDuckGo for: "{search_query}"')
            search_results = await search_duckduckgo(search_query)
            if cancelled: raise Exception("Processing cancelled by user during DuckDuckGo search.")
            if not search_results: 
                print('DuckDuckGo search failed or returned no results.')
                return None
        
        fetched_contents = []
        if search_source == 'DuckDuckGo':
            print(f"Fetching content for top {len(search_results)} DuckDuckGo results...")
            fetch_promises = [fetch_content_from_url(result["url"]) for result in search_results]
            fetched_contents = await asyncio.gather(*fetch_promises)
            if cancelled: raise Exception("Processing cancelled by user during DuckDuckGo content fetching.")
            print(f"Finished fetching content for DuckDuckGo results.")
        else:
            print("Using snippets directly from Tavily results.")
            fetched_contents = [result["content"] for result in search_results]

        if cancelled: raise Exception("Processing cancelled by user before combining content.")

        if fetched_contents:
            print(f"Combining {len(fetched_contents)} fetched/snippet contents.")
            combined_content = f'Research context for "{search_query}" (via {search_source}):\n\n'
            for i, result in enumerate(search_results):
                combined_content += f"Result {i + 1}:\n"
                combined_content += f"Title: {result['title']}\n"
                combined_content += f"URL: {result['url']}\n"
                combined_content += f"{search_source if search_source == 'Tavily' else 'Content'}: {fetched_contents[i] if fetched_contents[i] else '[No content available]'}\n\n"

            estimated_tokens_count = estimate_tokens(combined_content)
            max_tokens = SETTINGS.get("MAX_RESEARCH_CONTENT_TOKENS", 3000)
            print(f"Estimated research context tokens: {estimated_tokens_count}. Limit: {max_tokens}")
            if estimated_tokens_count > max_tokens:
                max_chars = max_tokens * 4
                combined_content = combined_content[:max_chars] + "\n\n[...research context truncated due to token limit]"
                print(f"Truncated research context to ~{max_tokens} tokens.")
            return combined_content.strip()
        else:
            print('No content could be obtained from search results.')
            return None

    except Exception as e:
        print(f'Error in _perform_research catch block for "{topic}": {e}')
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
        processed_chunks.append(llm_response)

    processed_content = "\n\n".join(processed_chunks).replace("\n\n\n", "\n\n").strip()

    final_content = cleanup_latex_delimiters(processed_content)
    final_content = refine_mermaid_blocks(final_content)

    lines = final_content.split('\n')
    if lines and lines[0].strip() == '\\boxed{':
        lines.pop(0)
        if lines and lines[-1].strip() == '}':
            lines.pop()
        final_content = '\n'.join(lines)

    if SETTINGS.get("REMOVE_CODE_FENCES_ON_ADD_LINKS", False):
        final_content = final_content.replace("```markdown", "")
        final_content = final_content.replace("```", "")
    else:
        final_content = final_content.replace("```markdown", "")

    await handle_duplicates(final_content)

    return final_content

async def generate_content_for_title(title: str, cancelled: bool = False) -> str:
    print(f"Starting content generation for: {title}")
    provider_config = get_provider_for_task("generateTitle")
    if not provider_config: raise ValueError("No valid LLM provider configured for \"Generate from Title\" task.")
    model_name = get_model_for_task("generateTitle", provider_config)

    research_context = ''
    if SETTINGS.get("ENABLE_RESEARCH_IN_GENERATE_CONTENT", False):
        if cancelled: raise Exception("Processing cancelled by user before research.")
        print(f'Research enabled for "{title}". Performing web search...')
        try:
            context = await _perform_research(title, cancelled)
            if cancelled: raise Exception("Processing cancelled by user during research.")
            if context:
                research_context = context
                print(f'Research context obtained for "{title}".')
            else:
                print(f'Warning: Research for "{title}" returned no results or failed.')
        except Exception as e:
            if "cancelled by user" in str(e): raise e
            print(f'Error during research for "{title}": {e}. Proceeding without web context.')
    else:
        print("Research disabled for \"Generate from Title\".")
    if cancelled: raise Exception("Processing cancelled by user before generation prompt construction.")

    research_context_section = f"\n\nUse the following research context to inform the documentation:\n\n{research_context}\n\n" if research_context else ""
    
    custom_prompt_template = SETTINGS.get("CUSTOM_PROMPT_GENERATE_TITLE")
    if not custom_prompt_template:
        raise ValueError("Custom prompt for 'Generate from Title' is not configured.")
    generation_prompt = custom_prompt_template.format(TITLE=title, RESEARCH_CONTEXT_SECTION=research_context_section)

    target_language_name = next((lang["name"] for lang in SETTINGS.get("AVAILABLE_LANGUAGES", []) if lang["code"] == SETTINGS.get("LANGUAGE", "en")), SETTINGS.get("LANGUAGE", "en"))
    if SETTINGS.get("LANGUAGE", "en") != "en":
        generation_prompt += f'\n\nIMPORTANT: Process the request and perform all reasoning in English. However, the final output MUST be written in {target_language_name}.In mermaid diagrams, it is necessary to translate into {target_language_name} while retaining the English.'

    if cancelled: raise Exception("Processing cancelled by user before API call.")
    print(f"Calling {provider_config['name']} to generate content...")

    generated_content = await call_llm_api(provider_config, model_name, generation_prompt, "", cancelled)

    if cancelled: raise Exception("Processing cancelled by user after API call.")
    print(f"Content received from {provider_config['name']}.")

    final_content = cleanup_latex_delimiters(generated_content)
    if cancelled: raise Exception("Processing cancelled by user during post-processing.")
    final_content = refine_mermaid_blocks(final_content)
    print("Mermaid/LaTeX cleanup applied.")

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
    print(f'Starting research for topic: "{topic}"')

    if cancelled: raise Exception("Processing cancelled by user before research.")
    research_context = await _perform_research(topic, cancelled)

    if cancelled: raise Exception("Processing cancelled by user during research.")

    if not research_context:
        raise ValueError(f'Research for "{topic}" failed or returned no results. Summary not generated.')
    print(f'_perform_research returned context for "{topic}" (length: {len(research_context)}).')

    provider_config = get_provider_for_task("research")
    if not provider_config: raise ValueError("No valid LLM provider configured for the \"Research & Summarize\" task.")
    model_name = get_model_for_task("research", provider_config)
    print(f'Using provider "{provider_config["name"]}" and model "{model_name}" for summarization.')

    if cancelled: raise Exception("Processing cancelled by user before summarization.")

    summary_prompt_template = SETTINGS.get("CUSTOM_PROMPT_RESEARCH_SUMMARIZE")
    if not summary_prompt_template:
        raise ValueError("Custom prompt for 'Research & Summarize' is not configured.")
    summary_prompt = summary_prompt_template.format(TOPIC=topic, SEARCH_RESULTS_CONTEXT=research_context)

    summary = await call_llm_api(provider_config, model_name, summary_prompt, "", cancelled)

    if cancelled: raise Exception("Processing cancelled by user after summarization.")

    print(f"Generated summary using {provider_config['name']}.")

    final_summary = cleanup_latex_delimiters(summary)
    if cancelled: raise Exception("Processing cancelled by user during post-processing.")
    final_summary = refine_mermaid_blocks(final_summary)
    print("Mermaid/LaTeX cleanup applied to summary.")

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
    print(f"Executing custom prompt...")
    provider_config = get_provider_for_task("addLinks") # Use default provider for custom tasks
    if not provider_config:
        raise ValueError(f"Active provider not found in settings.")
    model_name = get_model_for_task("addLinks", provider_config)

    llm_response = await call_llm_api(provider_config, model_name, prompt, content, cancelled)

    return llm_response

# --- File Utilities ---

async def handle_file_rename(old_path: str, new_path: str):
    old_name = os.path.splitext(os.path.basename(old_path))[0]
    new_name = os.path.splitext(os.path.basename(new_path))[0]

    if not old_name or not new_name or old_name == new_name:
        return

    print(f"Updating links for renamed file: {new_name}")

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
                    print(error_msg)
                    errors.append(error_msg)
    
    print(f"Updated links to \"{new_name}\" in {updated_count} files.")
    if errors:
        print(f"Encountered {len(errors)} errors while updating links.")

async def handle_file_delete(path: str):
    file_name = os.path.splitext(os.path.basename(path))[0]
    if not file_name:
        return

    print(f"Removing links for deleted file: {file_name}")

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
                    print(error_msg)
                    errors.append(error_msg)

    print(f"Removed links to \"{file_name}\" from {updated_count} files.")
    if errors:
        print(f"Encountered {len(errors)} errors while removing links.")

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
                    with open(file_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    
                    processed_content = cleanup_latex_delimiters(original_content)
                    processed_content = refine_mermaid_blocks(processed_content)

                    if processed_content.strip() != original_content.strip():
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(processed_content)
                        modified_count += 1
                        print(f"Fixed syntax in: {file_path}")
                except Exception as e:
                    error_msg = f"Error fixing syntax in {file_path}: {e}"
                    print(error_msg)
                    errors.append({"file": file_path, "message": str(e)})
    
    return {"errors": errors, "modified_count": modified_count}
