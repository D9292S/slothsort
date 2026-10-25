"""
AI categorization and fallback classification logic using Ollama and local open-weight models.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable
from pydantic import BaseModel, Field, ValidationError

from slothsort.config import (
    DEFAULT_CATEGORIES,
    EXTENSION_MAP,
    FALLBACK_MODELS,
    MAX_FILE_SIZE_MB,
    SortConfig,
)
from slothsort.scanner import FileEntry


class FileClassification(BaseModel):
    """Pydantic schema for individual file categorization output from LLM."""

    original: str
    category: str
    renamed: str = Field(default="")
    reason: str = Field(default="")


class CategorizationResult(BaseModel):
    """Processed result for a file containing decision metadata."""

    file_entry: FileEntry
    category: str
    new_name: str
    reason: str = ""
    source: str  # "ai" or "fallback"

    @property
    def is_renamed(self) -> bool:
        return self.new_name != self.file_entry.name

    model_config = {
        "arbitrary_types_allowed": True,
    }


def is_safe_rename(original_name: str, suggested_name: str, other_files: list[str]) -> bool:
    """
    Validate that the LLM did not hallucinate or cross-contaminate names by borrowing
    words from other files in the same batch.
    """
    orig_path = Path(original_name)
    sugg_path = Path(suggested_name)

    orig_stem = orig_path.stem.lower()
    sugg_stem = sugg_path.stem.lower()

    if orig_stem == sugg_stem:
        return True

    # Extract significant alphanumeric tokens (>= 3 chars)
    orig_tokens = set(re.findall(r"[a-z0-9]{3,}", orig_stem))
    sugg_tokens = set(re.findall(r"[a-z0-9]{3,}", sugg_stem))

    # Check for tokens belonging exclusively to other files in the batch
    other_tokens = set()
    for o in other_files:
        if o.lower() != original_name.lower():
            other_tokens.update(re.findall(r"[a-z0-9]{3,}", Path(o).stem.lower()))

    # If the suggestion borrows a distinct token from another file in the batch,
    # and that token is NOT present in the original filename, reject cross-contamination
    borrowed = (sugg_tokens & other_tokens) - orig_tokens
    if borrowed:
        return False

    # For installers/executables, software identity must be preserved
    ext = orig_path.suffix.lower()
    if ext in (".exe", ".msi", ".msix", ".dmg", ".deb", ".appimage", ".pkg"):
        orig_alpha = set(re.findall(r"[a-z]{3,}", orig_stem))
        sugg_alpha = set(re.findall(r"[a-z]{3,}", sugg_stem))
        if orig_alpha and sugg_alpha:
            has_overlap = any(
                s in orig_stem or o in sugg_stem
                for s in sugg_alpha
                for o in orig_alpha
            )
            if not has_overlap:
                return False

    return True


def sanitize_filename(filename: str, original_ext: str) -> str:
    """Ensure suggested filename is safe for the filesystem and retains its extension."""
    clean = filename.strip()
    # Remove forbidden characters for cross-platform safety
    clean = re.sub(r'[\\/*?:"<>|]', "", clean)
    clean = clean.strip(". ")

    if not clean:
        return f"file{original_ext}"

    # Verify extension retention
    if original_ext and not clean.lower().endswith(original_ext.lower()):
        clean = f"{clean}{original_ext}"

    return clean


def classify_by_extension(file_entry: FileEntry, no_rename: bool = False) -> CategorizationResult:
    """Deterministic fallback classification based on file extension and basic naming rules."""
    ext = file_entry.extension.lower()
    category = EXTENSION_MAP.get(ext, "Misc")

    # Basic cleanup if rename is permitted
    if no_rename:
        new_name = file_entry.name
        reason = "kept original name"
    else:
        # Tidy up common patterns: spaces/underscores to hyphens, collapse duplicates
        stem = file_entry.path.stem
        cleaned_stem = re.sub(r"\s*\(copy\)\s*", "", stem, flags=re.IGNORECASE)
        cleaned_stem = re.sub(r"[\s_]+", "-", cleaned_stem).lower()
        cleaned_stem = re.sub(r"-+", "-", cleaned_stem).strip("-")
        new_name = f"{cleaned_stem}{file_entry.extension}" if cleaned_stem else file_entry.name
        reason = "standardized kebab-case"

    return CategorizationResult(
        file_entry=file_entry,
        category=category,
        new_name=new_name,
        reason=reason,
        source="fallback",
    )


def build_prompt(files: list[FileEntry], valid_categories: list[str]) -> str:
    """Generate structured prompt for the local LLM with optional content snippets."""
    file_lines = []
    for f in files:
        line = f"- Name: {f.name} | Ext: {f.extension} | Size: {f.size_formatted}"
        if f.snippet:
            # Truncate snippet to 120 chars for prompt compactness
            safe_snip = f.snippet[:120].replace('"', "'")
            line += f' | Content: "{safe_snip}"'
        file_lines.append(line)

    file_list_str = "\n".join(file_lines)
    categories_str = ", ".join(valid_categories)

    prompt = f"""You are an accurate, careful file organization assistant. I will give you a list of files with their names, extensions, sizes, and optional content snippets.
For each file, respond with a JSON array where each element has:
- "original": the exact original filename
- "category": one of [{categories_str}]
- "renamed": a cleaner, meaningful filename (keep extension). If already clean or if it is an app/installer, keep the real app name.
- "reason": a short 3-6 word rationale for the categorization/name

CRITICAL RULES:
1. NEVER swap or borrow names between different files in the list. Each file must be judged ONLY by its own name and content.
2. For software/installers (.exe, .msi, .msix, etc.): ALWAYS keep the real application name (e.g. "ABDownloadManager_1.11.1.exe" -> "ab-download-manager-1.11.1.exe"). NEVER rename an application to a different product.
3. For image timestamps or camera uploads (e.g. "Screenshot 2024-10-15..."): standardize to kebab-case date. If a file is just a random timestamp or number (like "1792294654173.jpg") and you don't know what it is, KEEP the original name.
4. Rename suggestions should only clean up formatting (lowercase-kebab-case, remove noise/hashes/guids). DO NOT invent completely new subject names.
5. ONLY output valid JSON array, no conversational markdown or explanation.

Files:
{file_list_str}"""
    return prompt


def get_installed_models() -> set[str]:
    """Return set of installed model names in local Ollama."""
    try:
        import ollama
        client = ollama.Client()
        data = client.list()
        installed = set()
        model_list = data.get("models", []) if isinstance(data, dict) else getattr(data, "models", [])
        for m in model_list:
            name = m.get("name", "") if isinstance(m, dict) else (getattr(m, "model", "") or getattr(m, "name", ""))
            if name:
                installed.add(name)
                installed.add(name.split(":")[0])
        return installed
    except Exception:
        return set()


def parse_llm_json(response_text: str) -> list[FileClassification]:
    """Parse and validate JSON response from Ollama, supporting list or dict wrappers."""
    text = response_text.strip()

    # Strip markdown code blocks
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    raw_data = None
    try:
        raw_data = json.loads(text)
    except Exception:
        # Try extracting JSON array slice
        start_arr = text.find("[")
        end_arr = text.rfind("]")
        if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
            try:
                raw_data = json.loads(text[start_arr : end_arr + 1])
            except Exception:
                pass

        if raw_data is None:
            # Try extracting JSON object slice
            start_obj = text.find("{")
            end_obj = text.rfind("}")
            if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
                try:
                    raw_data = json.loads(text[start_obj : end_obj + 1])
                except Exception:
                    pass

    if raw_data is None:
        raise ValueError("Could not parse JSON from model response")

    # If wrapped in a dictionary (e.g. {"files": [...]} or {"results": [...]})
    if isinstance(raw_data, dict):
        for key in ["files", "results", "items", "data", "classifications"]:
            if isinstance(raw_data.get(key), list):
                raw_data = raw_data[key]
                break
        else:
            # Check if any dict value is a list of dicts
            for val in raw_data.values():
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    raw_data = val
                    break
            else:
                # If dict itself represents a single item
                if "original" in raw_data and "category" in raw_data:
                    raw_data = [raw_data]
                else:
                    raise ValueError("Model JSON object does not contain file list")

    if not isinstance(raw_data, list):
        raise ValueError("Model response is not a valid list of files")

    parsed_items: list[FileClassification] = []
    for item in raw_data:
        try:
            parsed_items.append(FileClassification.model_validate(item))
        except ValidationError:
            continue

    return parsed_items


def is_ollama_available() -> bool:
    """Check if local Ollama daemon is active and responding."""
    try:
        import ollama
        client = ollama.Client()
        client.list()
        return True
    except Exception:
        return False


def query_ollama(
    model: str,
    prompt: str,
    verbose: bool = False,
) -> str:
    """Query Ollama local model with JSON format enforced."""
    import ollama
    client = ollama.Client()

    response = client.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        format="json",
        options={"temperature": 0.1},
    )
    return response["message"]["content"]


def categorize_batch(
    files: list[FileEntry],
    config: SortConfig,
    log_func: Callable[[str], None] | None = None,
) -> list[CategorizationResult]:
    """
    Categorize a batch of files using local LLM, falling back to rule-based classification.
    """
    valid_categories = list(config.categories.keys())
    results: list[CategorizationResult] = []

    # Route duplicates and ultra-large files directly
    ai_candidates: list[FileEntry] = []
    for f in files:
        if f.is_duplicate and f.duplicate_of:
            results.append(
                CategorizationResult(
                    file_entry=f,
                    category="Duplicates",
                    new_name=f.name,
                    reason=f"duplicate of {f.duplicate_of.name}",
                    source="dedupe",
                )
            )
        elif f.size_mb > MAX_FILE_SIZE_MB:
            results.append(classify_by_extension(f, no_rename=config.no_rename))
        else:
            ai_candidates.append(f)

    if not ai_candidates:
        return results

    prompt = build_prompt(ai_candidates, valid_categories)
    parsed_classes: list[FileClassification] = []

    installed = get_installed_models()
    models_to_try = [config.model]
    for fb in FALLBACK_MODELS:
        if fb != config.model and fb not in models_to_try:
            # Only add fallback model if installed locally
            if not installed or fb in installed:
                models_to_try.append(fb)

    success = False
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                if log_func and config.verbose:
                    log_func(f"Querying Ollama model '{model_name}' (attempt {attempt + 1})...")

                raw_json = query_ollama(model_name, prompt, verbose=config.verbose)
                parsed_classes = parse_llm_json(raw_json)

                if parsed_classes:
                    success = True
                    break
            except Exception as ex:
                if log_func and config.verbose:
                    log_func(f"Ollama attempt failed with {model_name}: {ex}")
                continue

        if success:
            break

    # Map classifications by original filename
    class_map: dict[str, FileClassification] = {
        item.original.strip().lower(): item for item in parsed_classes
    }

    all_candidate_names = [f.name for f in ai_candidates]

    for file_entry in ai_candidates:
        match = class_map.get(file_entry.name.strip().lower())
        if match and match.category in config.categories:
            cat = match.category
            suggested_name = match.renamed.strip()

            if config.no_rename or not suggested_name:
                renamed = file_entry.name
                reason = match.reason or "categorized"
            else:
                candidate_clean = sanitize_filename(suggested_name, file_entry.extension)
                # Verify safety: check for hallucinations or cross-contamination
                if is_safe_rename(file_entry.name, candidate_clean, all_candidate_names):
                    renamed = candidate_clean
                    reason = match.reason or "standardized format"
                else:
                    # Safe fallback for this file: standardize original stem without hallucinating
                    fallback_res = classify_by_extension(file_entry)
                    renamed = fallback_res.new_name
                    reason = "standardized format (safety guarded)"

            results.append(
                CategorizationResult(
                    file_entry=file_entry,
                    category=cat,
                    new_name=renamed,
                    reason=reason,
                    source="ai",
                )
            )
        else:
            results.append(classify_by_extension(file_entry, no_rename=config.no_rename))

    return results


def categorize_files(
    files: list[FileEntry],
    config: SortConfig,
    progress_callback: Callable[[int, int], None] | None = None,
    log_func: Callable[[str], None] | None = None,
) -> list[CategorizationResult]:
    """
    Categorize all files in batches with resilience against model or connection failures.
    """
    results: list[CategorizationResult] = []
    total = len(files)
    batch_size = max(1, config.batch_size)

    # Check Ollama upfront
    ollama_ready = is_ollama_available()
    if not ollama_ready:
        if log_func:
            log_func("[yellow]Ollama offline: using deterministic extension taxonomy[/yellow]")
        for f in files:
            if f.is_duplicate and f.duplicate_of:
                results.append(
                    CategorizationResult(
                        file_entry=f,
                        category="Duplicates",
                        new_name=f.name,
                        reason=f"duplicate of {f.duplicate_of.name}",
                        source="dedupe",
                    )
                )
            else:
                results.append(classify_by_extension(f, no_rename=config.no_rename))
        if progress_callback:
            progress_callback(total, total)
        return results

    for i in range(0, total, batch_size):
        batch = files[i : i + batch_size]
        batch_results = categorize_batch(batch, config, log_func=log_func)
        results.extend(batch_results)
        if progress_callback:
            progress_callback(min(i + batch_size, total), total)

    return results
