# main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import json
import base64
import os
import binascii

import config
import notemd_core

def apply_user_config():
    """Applies user configuration from an environment variable."""
    config_str = os.environ.get('NOTEMD_CONFIG')
    if config_str:
        print("Found configuration in environment variable. Applying...")
        try:
            decoded_config = base64.b64decode(config_str).decode('utf-8')
            user_config = json.loads(decoded_config)
            for key, value in user_config.items():
                if hasattr(config, key):
                    print(f"Overriding config: {key} = {value}")
                    setattr(config, key, value)
        except (json.JSONDecodeError, binascii.Error, Exception) as e:
            print(f"Error processing config from environment variable: {e}")
    else:
        print("No custom configuration found in environment variables.")

# Apply config when module is loaded
apply_user_config()

# Set settings in notemd_core after applying any user config
notemd_core.set_settings({
    "DEFAULT_PROVIDERS": config.DEFAULT_PROVIDERS,
    "ACTIVE_PROVIDER": config.ACTIVE_PROVIDER,
    "CHUNK_WORD_COUNT": config.CHUNK_WORD_COUNT,
    "MAX_TOKENS": config.MAX_TOKENS,
    "ENABLE_DUPLICATE_DETECTION": config.ENABLE_DUPLICATE_DETECTION,
    "VAULT_ROOT": config.VAULT_ROOT,
    "CONCEPT_NOTE_FOLDER": config.CONCEPT_NOTE_FOLDER,
    "PROCESSED_FILE_FOLDER": config.PROCESSED_FILE_FOLDER,
    "CONCEPT_LOG_FOLDER": config.CONCEPT_LOG_FOLDER,
    "CONCEPT_LOG_FILE_NAME": config.CONCEPT_LOG_FILE_NAME,
    "TAVILY_API_KEY": config.TAVILY_API_KEY,
    "SEARCH_PROVIDER": config.SEARCH_PROVIDER,
    "DDG_MAX_RESULTS": config.DDG_MAX_RESULTS,
    "DDG_FETCH_TIMEOUT": config.DDG_FETCH_TIMEOUT,
    "MAX_RESEARCH_CONTENT_TOKENS": config.MAX_RESEARCH_CONTENT_TOKENS,
    "ENABLE_RESEARCH_IN_GENERATE_CONTENT": config.ENABLE_RESEARCH_IN_GENERATE_CONTENT,
    "TAVILY_MAX_RESULTS": config.TAVILY_MAX_RESULTS,
    "TAVILY_SEARCH_DEPTH": config.TAVILY_SEARCH_DEPTH,
    "ENABLE_STABLE_API_CALL": config.ENABLE_STABLE_API_CALL,
    "API_CALL_INTERVAL": config.API_CALL_INTERVAL,
    "API_CALL_MAX_RETRIES": config.API_CALL_MAX_RETRIES,
    "USE_MULTI_MODEL_SETTINGS": config.USE_MULTI_MODEL_SETTINGS,
    "ADD_LINKS_PROVIDER": config.ADD_LINKS_PROVIDER,
    "RESEARCH_PROVIDER": config.RESEARCH_PROVIDER,
    "GENERATE_TITLE_PROVIDER": config.GENERATE_TITLE_PROVIDER,
    "TRANSLATE_PROVIDER": config.TRANSLATE_PROVIDER,
    "SUMMARIZE_TO_MERMAID_PROVIDER": config.SUMMARIZE_TO_MERMAID_PROVIDER,
    "EXTRACT_CONCEPTS_PROVIDER": config.EXTRACT_CONCEPTS_PROVIDER,
    "EXTRACT_ORIGINAL_TEXT_PROVIDER": config.EXTRACT_ORIGINAL_TEXT_PROVIDER,
    "DIAGRAM_PROVIDER": config.DIAGRAM_PROVIDER,
    "ADD_LINKS_MODEL": config.ADD_LINKS_MODEL,
    "RESEARCH_MODEL": config.RESEARCH_MODEL,
    "GENERATE_TITLE_MODEL": config.GENERATE_TITLE_MODEL,
    "TRANSLATE_MODEL": config.TRANSLATE_MODEL,
    "SUMMARIZE_TO_MERMAID_MODEL": config.SUMMARIZE_TO_MERMAID_MODEL,
    "EXTRACT_CONCEPTS_MODEL": config.EXTRACT_CONCEPTS_MODEL,
    "EXTRACT_ORIGINAL_TEXT_MODEL": config.EXTRACT_ORIGINAL_TEXT_MODEL,
    "DIAGRAM_MODEL": config.DIAGRAM_MODEL,
    "REMOVE_CODE_FENCES_ON_ADD_LINKS": config.REMOVE_CODE_FENCES_ON_ADD_LINKS,
    "LANGUAGE": config.LANGUAGE,
    "AVAILABLE_LANGUAGES": config.AVAILABLE_LANGUAGES,
    "ENABLE_GLOBAL_CUSTOM_PROMPTS": config.ENABLE_GLOBAL_CUSTOM_PROMPTS,
    "CUSTOM_PROMPT_ADD_LINKS": config.CUSTOM_PROMPT_ADD_LINKS,
    "CUSTOM_PROMPT_GENERATE_TITLE": config.CUSTOM_PROMPT_GENERATE_TITLE,
    "CUSTOM_PROMPT_RESEARCH_SUMMARIZE": config.CUSTOM_PROMPT_RESEARCH_SUMMARIZE,
    "CUSTOM_PROMPT_TRANSLATE": config.CUSTOM_PROMPT_TRANSLATE,
    "CUSTOM_PROMPT_SUMMARIZE_TO_MERMAID": config.CUSTOM_PROMPT_SUMMARIZE_TO_MERMAID,
    "CUSTOM_PROMPT_GENERATE_DIAGRAM": config.CUSTOM_PROMPT_GENERATE_DIAGRAM,
    "CUSTOM_PROMPT_EXTRACT_CONCEPTS": config.CUSTOM_PROMPT_EXTRACT_CONCEPTS,
    "CUSTOM_PROMPT_EXTRACT_ORIGINAL_TEXT": config.CUSTOM_PROMPT_EXTRACT_ORIGINAL_TEXT,
})

app = FastAPI(
    title="Notemd MCP Server",
    description="MCP server for Notemd Obsidian plugin functionalities",
    version="0.6.1",
)

class ProcessContentRequest(BaseModel):
    content: str
    cancelled: bool = False

class GenerateTitleRequest(BaseModel):
    title: str
    cancelled: bool = False

class ResearchSummarizeRequest(BaseModel):
    topic: str
    cancelled: bool = False

class FileRenameRequest(BaseModel):
    old_path: str
    new_path: str

class FileDeleteRequest(BaseModel):
    path: str

class BatchFixMermaidRequest(BaseModel):
    folder_path: str

class CustomPromptRequest(BaseModel):
    prompt: str
    content: str
    cancelled: bool = False

class TranslateContentRequest(BaseModel):
    content: str
    target_language: str = "en"
    cancelled: bool = False

class SummarizeMermaidRequest(BaseModel):
    content: str
    target_language: str = "en"
    cancelled: bool = False

class GenerateDiagramRequest(BaseModel):
    content: str
    diagram_intent: str = "auto"
    target_language: str = "en"
    compatibility_mode: str = "canonical"
    cancelled: bool = False

class ExtractConceptsRequest(BaseModel):
    content: str
    cancelled: bool = False

class ExtractOriginalTextRequest(BaseModel):
    reference_content: str
    user_input: str
    cancelled: bool = False

class CheckDuplicatesRequest(BaseModel):
    content: str

@app.post("/process_content", summary="Process Content (Add Links)")
async def process_content_endpoint(request: ProcessContentRequest):
    """Process content using Notemd core logic to add wiki-links."""
    try:
        processed_text = await notemd_core.process_content(request.content, request.cancelled)
        return {"processed_content": processed_text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/generate_title", summary="Generate Content from Title")
async def generate_title_endpoint(request: GenerateTitleRequest):
    """Generate content for a given title."""
    try:
        generated_content = await notemd_core.generate_content_for_title(request.title, request.cancelled)
        return {"generated_content": generated_content}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/research_summarize", summary="Research and Summarize Topic")
async def research_summarize_endpoint(request: ResearchSummarizeRequest):
    """Perform web research and summarize a topic."""
    try:
        summary = await notemd_core.research_and_summarize(request.topic, request.cancelled)
        return {"summary": summary}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/execute_custom_prompt", summary="Execute Custom Prompt")
async def execute_custom_prompt_endpoint(request: CustomPromptRequest):
    """Execute a user-defined prompt with given content."""
    try:
        response = await notemd_core.execute_custom_prompt(request.prompt, request.content, request.cancelled)
        return {"response": response}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/translate_content", summary="Translate Content")
async def translate_content_endpoint(request: TranslateContentRequest):
    """Translate content to the target language."""
    try:
        translated = await notemd_core.translate_content(
            request.content,
            request.target_language,
            request.cancelled
        )
        return {"translated_content": translated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/summarize_as_mermaid", summary="Summarize as Mermaid")
async def summarize_as_mermaid_endpoint(request: SummarizeMermaidRequest):
    """Generate a Mermaid mindmap summary from content."""
    try:
        summary = await notemd_core.summarize_as_mermaid(
            request.content,
            request.target_language,
            request.cancelled
        )
        return {"mermaid_summary": summary}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/generate_diagram", summary="Generate Diagram")
async def generate_diagram_endpoint(request: GenerateDiagramRequest):
    """Generate a diagram artifact from content using canonical diagram flow."""
    try:
        diagram = await notemd_core.generate_diagram(
            request.content,
            request.diagram_intent,
            request.target_language,
            request.compatibility_mode,
            request.cancelled
        )
        return {"diagram": diagram}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/generate_experimental_diagram", summary="Generate Experimental Diagram (Legacy Alias)")
async def generate_experimental_diagram_endpoint(request: GenerateDiagramRequest):
    """Legacy alias for diagram generation compatibility."""
    try:
        diagram = await notemd_core.generate_diagram(
            request.content,
            request.diagram_intent,
            request.target_language,
            "legacy-mermaid",
            request.cancelled
        )
        return {"diagram": diagram}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/preview_diagram", summary="Preview Diagram")
async def preview_diagram_endpoint(request: GenerateDiagramRequest):
    """Generate previewable diagram content (no file side effects)."""
    try:
        diagram = await notemd_core.generate_diagram(
            request.content,
            request.diagram_intent,
            request.target_language,
            request.compatibility_mode,
            request.cancelled
        )
        return {"diagram": diagram}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/preview_experimental_diagram", summary="Preview Experimental Diagram (Legacy Alias)")
async def preview_experimental_diagram_endpoint(request: GenerateDiagramRequest):
    """Legacy preview alias that normalizes to canonical preview flow."""
    try:
        diagram = await notemd_core.generate_diagram(
            request.content,
            request.diagram_intent,
            request.target_language,
            "legacy-mermaid",
            request.cancelled
        )
        return {"diagram": diagram}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/extract_concepts", summary="Extract Concepts")
async def extract_concepts_endpoint(request: ExtractConceptsRequest):
    """Extract core concepts from content."""
    try:
        concepts = await notemd_core.extract_concepts(request.content, request.cancelled)
        return {"concepts": concepts}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/extract_original_text", summary="Extract Original Text")
async def extract_original_text_endpoint(request: ExtractOriginalTextRequest):
    """Extract matching verbatim excerpts for user inputs."""
    try:
        extracted = await notemd_core.extract_original_text(
            request.reference_content,
            request.user_input,
            request.cancelled
        )
        return {"extracted_text": extracted}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/check_duplicates", summary="Check Duplicates")
async def check_duplicates_endpoint(request: CheckDuplicatesRequest):
    """Return normalized duplicate terms detected in the content."""
    try:
        duplicates = notemd_core.get_duplicate_words(request.content)
        return {"duplicates": duplicates, "count": len(duplicates)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/handle_file_rename", summary="Handle File Rename")
async def handle_file_rename_endpoint(request: FileRenameRequest):
    """Update backlinks when a file is renamed."""
    try:
        await notemd_core.handle_file_rename(request.old_path, request.new_path)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/handle_file_delete", summary="Handle File Delete")
async def handle_file_delete_endpoint(request: FileDeleteRequest):
    """Remove backlinks when a file is deleted."""
    try:
        await notemd_core.handle_file_delete(request.path)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/batch_fix_mermaid", summary="Batch Fix Mermaid Syntax")
async def batch_fix_mermaid_endpoint(request: BatchFixMermaidRequest):
    """Fix Mermaid and LaTeX syntax in all Markdown files in a folder."""
    try:
        result = await notemd_core.batch_fix_mermaid_syntax_in_folder(request.folder_path)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.get("/health", summary="Health Check")
async def health_check():
    """Check if the server is running."""
    return {"status": "ok"}

def start_server():
    """Starts the uvicorn server."""
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    start_server()
