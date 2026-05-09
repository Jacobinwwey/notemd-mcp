#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import base64
import copy
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx
import tomllib


def load_toml(path: Path) -> Dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


def to_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    return bool(value)


def build_overrides(cfg: Dict[str, Any], base_config: Any) -> Dict[str, Any]:
    notemd = cfg.get("notemd", {})
    providers_cfg = cfg.get("providers", {})
    tavily_cfg = cfg.get("tavily", {})

    providers = copy.deepcopy(base_config.DEFAULT_PROVIDERS)

    provider_key_map = {
        "OpenAI": "openai_api_key",
        "DeepSeek": "deepseek_api_key",
        "Anthropic": "anthropic_api_key",
        "Google": "google_api_key",
        "Mistral": "mistral_api_key",
        "OpenRouter": "openrouter_api_key",
        "Azure OpenAI": "azure_openai_api_key",
    }
    provider_model_map = {
        "OpenAI": "openai_model",
        "DeepSeek": "deepseek_model",
        "Anthropic": "anthropic_model",
        "Google": "google_model",
        "Mistral": "mistral_model",
        "OpenRouter": "openrouter_model",
        "Azure OpenAI": "azure_openai_model",
        "Ollama": "ollama_model",
        "LMStudio": "lmstudio_model",
    }

    for provider in providers:
        name = provider.get("name")
        key_field = provider_key_map.get(name)
        model_field = provider_model_map.get(name)
        if key_field:
            key_val = providers_cfg.get(key_field, "")
            if key_val is not None:
                provider["apiKey"] = key_val
        if model_field:
            model_val = providers_cfg.get(model_field, "")
            if model_val:
                provider["model"] = model_val
        if name == "Azure OpenAI":
            base_url = providers_cfg.get("azure_openai_base_url")
            api_version = providers_cfg.get("azure_openai_api_version")
            if base_url is not None:
                provider["baseUrl"] = base_url
            if api_version is not None:
                provider["apiVersion"] = api_version

    active_provider = notemd.get("active_provider", base_config.ACTIVE_PROVIDER)
    language = notemd.get("language", base_config.LANGUAGE)

    overrides: Dict[str, Any] = {
        "DEFAULT_PROVIDERS": providers,
        "ACTIVE_PROVIDER": active_provider,
        "USE_MULTI_MODEL_SETTINGS": False,
        "SEARCH_PROVIDER": notemd.get("search_provider", base_config.SEARCH_PROVIDER),
        "TAVILY_API_KEY": tavily_cfg.get("api_key", base_config.TAVILY_API_KEY),
        "TAVILY_SEARCH_DEPTH": tavily_cfg.get("search_depth", base_config.TAVILY_SEARCH_DEPTH),
        "TAVILY_MAX_RESULTS": tavily_cfg.get("max_results", base_config.TAVILY_MAX_RESULTS),
        "LANGUAGE": language,
        "MAX_TOKENS": int(notemd.get("max_tokens", base_config.MAX_TOKENS)),
        "CHUNK_WORD_COUNT": int(notemd.get("chunk_word_count", base_config.CHUNK_WORD_COUNT)),
        "ENABLE_RESEARCH_IN_GENERATE_CONTENT": to_bool(
            notemd.get("enable_research_in_generate_content"), base_config.ENABLE_RESEARCH_IN_GENERATE_CONTENT
        ),
        "ENABLE_STABLE_API_CALL": to_bool(
            notemd.get("enable_stable_api_call"), base_config.ENABLE_STABLE_API_CALL
        ),
        "API_CALL_INTERVAL": int(notemd.get("api_call_interval", base_config.API_CALL_INTERVAL)),
        "API_CALL_MAX_RETRIES": int(notemd.get("api_call_max_retries", base_config.API_CALL_MAX_RETRIES)),
    }
    return overrides


def make_env_override_json(overrides: Dict[str, Any]) -> str:
    raw = json.dumps(overrides, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def write_test_vault(vault_root: Path) -> Tuple[Path, Path, Path]:
    if vault_root.exists():
        shutil.rmtree(vault_root)
    vault_root.mkdir(parents=True, exist_ok=True)

    old_path = vault_root / "Old Idea.md"
    new_path = vault_root / "Renamed Idea.md"
    ref_path = vault_root / "Ref.md"
    mermaid_path = vault_root / "BrokenMermaid.md"

    old_path.write_text("# Old Idea\nThis note explains an old idea.\n", encoding="utf-8")
    ref_path.write_text(
        "# Ref\nRelated to [[Old Idea]].\nAnd another mention of [[Old Idea]].\n",
        encoding="utf-8",
    )
    mermaid_path.write_text(
        "```(mermaid)\ngraph TD\nA --> B\n```\n",
        encoding="utf-8",
    )
    return old_path, new_path, vault_root


async def run_e2e(cfg: Dict[str, Any], keep_vault: bool = False) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    import config as base_config  # type: ignore

    overrides = build_overrides(cfg, base_config)
    test_data = cfg.get("test_data", {})
    tests_cfg = cfg.get("tests", {})

    vault_root = Path(test_data.get("vault_root", "/tmp/notemd-mcp-e2e-vault"))
    overrides["VAULT_ROOT"] = str(vault_root)
    os.environ["NOTEMD_CONFIG"] = make_env_override_json(overrides)

    import main  # type: ignore

    old_path, new_path, folder_path = write_test_vault(vault_root)

    run_llm = to_bool(tests_cfg.get("run_llm_endpoints"), True)
    run_generate_title = to_bool(tests_cfg.get("run_generate_title"), True)
    run_research = to_bool(tests_cfg.get("run_research_summarize"), False)
    target_language = tests_cfg.get("target_language", overrides.get("LANGUAGE", "en"))

    sample_markdown = test_data.get(
        "sample_markdown",
        "## Sample\nKnowledge graphs connect entities and relationships.",
    )
    reference_content = test_data.get(
        "reference_content",
        "Knowledge graphs encode entities and relationships.\nEntity resolution improves deduplication.",
    )
    user_input = test_data.get("user_input", "What improves deduplication?")
    title = test_data.get("title", "Knowledge Graph")
    topic = test_data.get("topic", "Knowledge graph in markdown systems")

    failures: List[str] = []

    async def call(
        client: httpx.AsyncClient, method: str, path: str, payload: Dict[str, Any] | None = None
    ) -> httpx.Response:
        if method == "GET":
            resp = await client.get(path)
        else:
            resp = await client.post(path, json=payload)
        return resp

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://notemd-e2e.local",
        timeout=180.0,
    ) as client:
        checks: List[Tuple[str, str, str, Dict[str, Any] | None, bool]] = [
            ("health", "GET", "/health", None, True),
            ("check_duplicates", "POST", "/check_duplicates", {"content": "alpha beta alpha"}, True),
            (
                "handle_file_rename",
                "POST",
                "/handle_file_rename",
                {"old_path": str(old_path), "new_path": str(new_path)},
                True,
            ),
            ("handle_file_delete", "POST", "/handle_file_delete", {"path": str(new_path)}, True),
            ("batch_fix_mermaid", "POST", "/batch_fix_mermaid", {"folder_path": str(folder_path)}, True),
        ]

        if run_llm:
            checks.extend(
                [
                    ("process_content", "POST", "/process_content", {"content": sample_markdown, "cancelled": False}, True),
                    (
                        "translate_content",
                        "POST",
                        "/translate_content",
                        {"content": sample_markdown, "target_language": target_language, "cancelled": False},
                        True,
                    ),
                    (
                        "summarize_as_mermaid",
                        "POST",
                        "/summarize_as_mermaid",
                        {"content": sample_markdown, "target_language": target_language, "cancelled": False},
                        True,
                    ),
                    (
                        "generate_diagram",
                        "POST",
                        "/generate_diagram",
                        {
                            "content": sample_markdown,
                            "diagram_intent": "mindmap",
                            "target_language": target_language,
                            "compatibility_mode": "canonical",
                            "cancelled": False,
                        },
                        True,
                    ),
                    (
                        "generate_experimental_diagram",
                        "POST",
                        "/generate_experimental_diagram",
                        {
                            "content": sample_markdown,
                            "diagram_intent": "mindmap",
                            "target_language": target_language,
                            "cancelled": False,
                        },
                        True,
                    ),
                    (
                        "preview_diagram",
                        "POST",
                        "/preview_diagram",
                        {
                            "content": sample_markdown,
                            "diagram_intent": "mindmap",
                            "target_language": target_language,
                            "compatibility_mode": "canonical",
                            "cancelled": False,
                        },
                        True,
                    ),
                    (
                        "preview_experimental_diagram",
                        "POST",
                        "/preview_experimental_diagram",
                        {
                            "content": sample_markdown,
                            "diagram_intent": "mindmap",
                            "target_language": target_language,
                            "cancelled": False,
                        },
                        True,
                    ),
                    ("extract_concepts", "POST", "/extract_concepts", {"content": sample_markdown, "cancelled": False}, True),
                    (
                        "extract_original_text",
                        "POST",
                        "/extract_original_text",
                        {
                            "reference_content": reference_content,
                            "user_input": user_input,
                            "cancelled": False,
                        },
                        True,
                    ),
                ]
            )
            if run_generate_title:
                checks.append(("generate_title", "POST", "/generate_title", {"title": title, "cancelled": False}, True))
            if run_research:
                checks.append(
                    ("research_summarize", "POST", "/research_summarize", {"topic": topic, "cancelled": False}, True)
                )

        for name, method, path, payload, required_ok in checks:
            try:
                resp = await call(client, method, path, payload)
                ok = 200 <= resp.status_code < 300
                if required_ok and not ok:
                    failures.append(f"{name}: HTTP {resp.status_code} -> {resp.text}")
                    print(f"[FAIL] {name}: HTTP {resp.status_code}")
                    continue

                if name in {"summarize_as_mermaid", "generate_diagram", "generate_experimental_diagram", "preview_diagram", "preview_experimental_diagram"}:
                    body = resp.json()
                    value = body.get("mermaid_summary") or body.get("diagram") or ""
                    if "```mermaid" not in value:
                        failures.append(f"{name}: response missing mermaid code fence")
                        print(f"[FAIL] {name}: no mermaid code fence")
                        continue

                if name == "check_duplicates":
                    body = resp.json()
                    if body.get("count") != 1:
                        failures.append(f"{name}: expected duplicate count 1, got {body}")
                        print(f"[FAIL] {name}: duplicate count mismatch")
                        continue

                if name == "handle_file_rename":
                    ref_after_rename = (vault_root / "Ref.md").read_text(encoding="utf-8")
                    if "[[Renamed Idea]]" not in ref_after_rename:
                        failures.append("file-ops: rename did not update backlinks as expected")
                        print("[FAIL] file-ops: rename backlink update missing")
                        continue
                    print("[OK] file-ops: rename backlink update")

                if name == "handle_file_delete":
                    ref_after_delete = (vault_root / "Ref.md").read_text(encoding="utf-8")
                    if "[[Renamed Idea]]" in ref_after_delete:
                        failures.append("file-ops: delete did not remove backlinks as expected")
                        print("[FAIL] file-ops: delete backlink removal missing")
                        continue
                    print("[OK] file-ops: delete backlink removal")

                print(f"[OK] {name}")
            except Exception as exc:
                failures.append(f"{name}: exception {exc}")
                print(f"[FAIL] {name}: {exc}")

    if not keep_vault:
        shutil.rmtree(vault_root, ignore_errors=True)

    if failures:
        print("\nE2E RESULT: FAIL")
        for item in failures:
            print(f"- {item}")
        return 1

    print("\nE2E RESULT: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live notemd-mcp E2E tests from TOML config")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to TOML config file (copy from live_e2e.template.toml)",
    )
    parser.add_argument(
        "--keep-vault",
        action="store_true",
        help="Keep test vault files after execution",
    )
    args = parser.parse_args()

    cfg_path = Path(args.config).resolve()
    if not cfg_path.exists():
        print(f"Config file not found: {cfg_path}")
        return 2

    cfg = load_toml(cfg_path)
    return asyncio.run(run_e2e(cfg, keep_vault=args.keep_vault))


if __name__ == "__main__":
    raise SystemExit(main())
