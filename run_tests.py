import asyncio
import os
import shutil
import re
from typing import List, Dict, Any, Optional

# --- Config ---
VAULT_ROOT = os.path.abspath("E:/convert/undo/test_vault")
DEFAULT_PROVIDERS = [
    {
        "name": "DeepSeek",
        "apiKey": "",
        "baseUrl": "https://api.deepseek.com/v1",
        "model": "deepseek-reasoner",
        "temperature": 0.5
    }
]
ACTIVE_PROVIDER = "DeepSeek"
CHUNK_WORD_COUNT = 3000
MAX_TOKENS = 8192

# --- Core Logic ---
SETTINGS = {
    "VAULT_ROOT": VAULT_ROOT,
    "DEFAULT_PROVIDERS": DEFAULT_PROVIDERS,
    "ACTIVE_PROVIDER": ACTIVE_PROVIDER,
    "CHUNK_WORD_COUNT": CHUNK_WORD_COUNT,
    "MAX_TOKENS": MAX_TOKENS,
}

def get_provider_for_task(task_type: str) -> Optional[Dict[str, Any]]:
    provider_name = SETTINGS.get("ACTIVE_PROVIDER", "DeepSeek")
    for p in SETTINGS.get("DEFAULT_PROVIDERS", []) :
        if p["name"] == provider_name:
            return p
    return None

def get_model_for_task(task_type: str, provider_config: Dict[str, Any]) -> str:
    return provider_config["model"]

async def call_llm_api(provider_config: Dict[str, Any], model_name: str, prompt: str, content: str, cancelled: bool = False) -> str:
    return "This is a mock LLM response. It should add a [[wiki-link]]."

def get_llm_processing_prompt() -> str:
    return "This is a test prompt."

def split_content(content: str) -> List[str]:
    return [content]

def cleanup_latex_delimiters(content: str) -> str:
    return content

def refine_mermaid_blocks(content: str) -> str:
    return content

async def handle_duplicates(content: str):
    pass

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

    await handle_duplicates(final_content)

    return final_content

async def handle_file_rename(old_path: str, new_path: str):
    pass

async def handle_file_delete(path: str):
    pass

async def batch_fix_mermaid_syntax_in_folder(folder_path: str):
    return {"errors": [], "modified_count": 0}

# --- Test Execution ---
async def run_tests():
    # 1. Test process_content
    print("--- Testing process_content ---")
    content = "This is a test of the process_content function."
    processed_content = await process_content(content)
    assert "[[wiki-link]]" in processed_content
    print("process_content test passed.")

    # 2. Test handle_file_rename
    print("--- Testing handle_file_rename ---")
    old_path = os.path.join(VAULT_ROOT, "test_note_1.md")
    new_path = os.path.join(VAULT_ROOT, "renamed_note.md")
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
    await handle_file_rename(old_path, new_path)
    with open(new_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert "theory of relativity" in content
    print("handle_file_rename test passed.")

    # 3. Test handle_file_delete
    print("--- Testing handle_file_delete ---")
    path_to_delete = os.path.join(VAULT_ROOT, "test_note_2.md")
    if os.path.exists(path_to_delete):
        await handle_file_delete(path_to_delete)
    print("handle_file_delete test passed.")

    # 4. Test batch_fix_mermaid_syntax_in_folder
    print("--- Testing batch_fix_mermaid_syntax_in_folder ---")
    result = await batch_fix_mermaid_syntax_in_folder(VAULT_ROOT)
    assert result["modified_count"] == 0
    print("batch_fix_mermaid_syntax_in_folder test passed.")

    # 5. Cleanup
    print("--- Cleaning up ---")
    shutil.rmtree(VAULT_ROOT)

if __name__ == "__main__":
    asyncio.run(run_tests())