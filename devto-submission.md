---
title: "SlothSort 🦥 — An Offline AI File Organizer That Does the Tidying So You Don't Have To"
published: true
description: "A local, privacy-first CLI tool using Ollama + Llama 3.2 that contextually sorts and renames messy folders. Zero cloud APIs, 100% offline, with watch mode and instant rollback."
tags: hacktoberfest, ai, opensource, python
cover_image: 
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19)*

---

## What I Built

Most developers have a `Downloads` or `Desktop` folder that looks like a digital archeology dig: dozens of files named `document(1).pdf`, `Screenshot 2026-10-21 000814.png`, `final_report_FINAL_v2_USETHISONE.docx`, and camera uploads like `IMG_20241019_142356.jpg`.

Organizing them by hand is tedious. Writing a simple bash script with `mv *.pdf Documents/` fails because `notes.txt` might be a meeting recap or a code snippet, camera uploads remain unsearchable, and duplicate downloads pile up unnoticed.

In the spirit of **International Sloth Day** and this week's theme — **Slow and Steady: build something with open-source AI that rewards laziness** — I built **[SlothSort](https://github.com/your-username/slothsort)**.

**SlothSort** is a terminal tool powered by a local open-weight model (`llama3.2`) running via **Ollama**. It inspects your messy directory, understands what each file actually is, standardizes filenames into clean kebab-case, and files them into categorized subdirectories.

### Key Capabilities

1. **Contextual Categorization:** Classifies files not just by extension, but by reading filename tokens and peeking at the first few lines of text/code/data files.
2. **Standardized Renaming:** Turns messy timestamps (`Screenshot 2026-10-21 000814.png`) and camera files (`IMG_20241019_142356.jpg`) into clean, human-readable names (`screenshot-2026-10-21-000814.png`, `photo-2024-10-19.jpg`).
3. **True Sloth Mode (`--watch`):** Runs continuously in the background, checking your directory every 60 seconds and organizing incoming downloads automatically while you take a nap.
4. **Cryptographic Deduplication (`--dedupe`):** Uses fast SHA-256 fingerprinting on matching file sizes to catch duplicate downloads (`invoice (1).pdf`) and isolate them into a dedicated `Duplicates/` folder.
5. **Defensive by Default:** Default mode is safe dry-run (`--dry-run`). Every real move (`--execute`) writes an atomic transaction manifest (`.slothsort-undo.json`), allowing single-command rollback (`slothsort undo`).

---

## Demo

Here is a live terminal session running against a messy directory:

```text
$ slothsort ~/Downloads --dedupe

┌──────────────── 🦥 slothsort v1.0.0 ────────────────┐
│  📂 /Users/deepa/Downloads                          │
│  ⚙️   DRY-RUN  Model: llama3.2 • Offline Inference  │
└─────────────────────────────────────────────────────┘

Taxonomy Breakdown                                                          
┌────────────────────┬──────────┬────────────┬────────────┬────────────────┐
│ Category           │    Files │       Size │    Renamed │      Inference │
├────────────────────┼──────────┼────────────┼────────────┼────────────────┤
│ 📦 Archives        │        3 │    45.0 MB │          1 │      1/3 local │
│ 🎵 Audio           │        2 │    18.5 MB │          2 │          rules │
│ 💻 Code            │        5 │     0.2 MB │          2 │          rules │
│ 📊 Data            │        3 │     1.1 MB │          3 │          rules │
│ 🎨 Design          │        2 │    24.0 MB │          2 │          rules │
│ 📄 Documents       │        7 │     2.8 MB │          6 │      1/7 local │
│ 📑 Duplicates      │        2 │     1.4 MB │          0 │         dedupe │
│ 🖼️  Images         │        4 │     6.9 MB │          4 │          rules │
│ ⚙️  Installers     │        2 │   157.9 MB │          2 │          rules │
│ 🎬 Videos          │        1 │   240.0 MB │          1 │      1/1 local │
├────────────────────┼──────────┼────────────┼────────────┼────────────────┤
│ Total              │       31 │   497.8 MB │         23 │              — │
└────────────────────┴──────────┴────────────┴────────────┴────────────────┘

┌─ Proposed Directory Hierarchy ──────────────────────────────────────────────┐
│ 📁 Downloads/                                                               │
│ ├── 📄 Documents/ (7 files)                                                 │
│ │   ├── analytics_october_metrics.csv → analytics-october-metrics.csv •     │
│ │   │   Financial data report                                               │
│ │   ├── budget_forecast_q4.xlsx → budget-forecast-q4.xlsx • standardized    │
│ │   │   kebab-case                                                          │
│ │   ├── final_report_FINAL_v3_USETHISONE.docx →                             │
│ │   │   final-report-final-v3-usethisone.docx • standardized kebab-case     │
│ │   └── meeting_notes_oct.txt → meeting-notes-oct.txt • standardized        │
│ │       kebab-case                                                          │
│ ├── 📑 Duplicates/ (2 files)                                                │
│ │   ├── document(2).pdf → Duplicates/document(2).pdf • duplicate of         │
│ │   │   document(1).pdf                                                     │
│ │   └── IMG_20241020_083211.jpg → Duplicates/IMG_20241020_083211.jpg •      │
│ │       duplicate of IMG_20241019_142356.jpg                                │
│ ├── 🖼️  Images/ (4 files)                                                   │
│ │   ├── Screenshot 2026-10-21 000814.png →                                  │
│ │   │   screenshot-2026-10-21-000814.png • standardized kebab-case          │
│ │   └── wallpaper_4k_mountain.jpg → wallpaper-4k-mountain.jpg •             │
│ │       standardized kebab-case                                             │
│ └── ⚙️  Installers/ (2 files)                                               │
│     ├── ABDownloadManager_1.11.1_windows_x64.exe →                          │
│     │   abdownloadmanager-1.11.1-windows-x64.exe • standardized kebab-case  │
│     └── VSCodeUserSetup-x64-1.92.0.exe → vscodeusersetup-x64-1.92.0.exe •   │
│         standardized kebab-case                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ Next Step ─────────────────────────────────────────────────────────────────┐
│  Dry-run preview complete. No files were modified on disk.                  │
│                                                                             │
│  To apply these changes, run:                                               │
│    slothsort "~/Downloads" --execute --dedupe                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

When you pass `--execute`, the moves happen atomically. If you ever change your mind:

```text
$ slothsort undo ~/Downloads

┌─ Rollback Complete ─────────────────────────────────────────────────────────┐
│  ✓ Successfully restored 31 file(s) to original locations.                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Code

The complete codebase, documentation, and automated test suite are open-sourced on GitHub:

👉 **[GitHub Repository: slothsort/slothsort](https://github.com/your-username/slothsort)**

```
slothsort/
├── pyproject.toml              # Modern Hatchling package configuration
├── README.md                   # Full documentation and command reference
├── LICENSE                     # MIT License
├── .slothsort.toml.example     # Configuration template for user overrides
├── slothsort/
│   ├── __init__.py             # Version metadata
│   ├── config.py               # Taxonomy mapping, model configurations, defaults
│   ├── scanner.py              # Filtering, snippet extraction, SHA-256 duplicate hashing
│   ├── categorizer.py          # Ollama JSON inference + Algorithmic Hallucination Guard
│   ├── organizer.py            # Collision resolution (-1, -2), moves, atomic undo manifest
│   └── cli.py                  # Rich terminal UI, diff tree, watch mode, commands
├── demo/
│   └── simulate_mess.py        # Demo script to generate 31 realistic messy files
└── tests/
    ├── test_scanner.py         # Filtering, snippets, duplicate detection tests
    ├── test_safety.py          # Hallucination guard & name preservation tests
    ├── test_parser.py          # Resilient JSON parsing tests (lists, dicts, markdown)
    └── test_organizer.py       # Collision resolution & end-to-end rollback tests
```

---

## How I Built It

SlothSort is built with **Python 3.10+**, **Ollama**, **Meta Llama 3.2 (3B)**, **Click**, **Rich**, and **Pydantic**.

### 1. Local Model Integration with Ollama
Inference runs through the official `ollama` Python SDK against a local endpoint (`http://localhost:11434`). Files are sent in batches of 15 to stay within the model's sweet spot for latency and attention.

### 2. Content Header Sniffing (Peeking)
Small models struggle with generic names like `notes.txt` or `export.csv` when relying solely on filenames. For text, CSV, JSON, and code files under 2 MB, `scanner.py` reads the first 300 characters, flattens whitespace, and provides it as a grounding context snippet. This allows the model to differentiate between a tax statement and meeting notes accurately.

### 3. The Cross-Contamination Hallucination Trap
During development with `llama3.2:3b`, I discovered an unexpected failure mode: when processing a batch containing multiple software installers (e.g., `ABDownloadManager...exe` and `bitdefender...exe`), the 3B model occasionally cross-pollinated names, suggesting `bitdefender.exe` as the new name for `ABDownloadManager`!

Silently renaming an application to a completely different software package is unacceptable. To solve this, I designed an algorithmic **Safety Guard** (`is_safe_rename`) in Python:

```python
def is_safe_rename(original_name: str, suggested_name: str, other_files: list[str]) -> bool:
    orig_path = Path(original_name)
    sugg_path = Path(suggested_name)

    orig_stem = orig_path.stem.lower()
    sugg_stem = sugg_path.stem.lower()

    if orig_stem == sugg_stem:
        return True

    # Check for tokens belonging exclusively to other files in the batch
    orig_tokens = set(re.findall(r"[a-z0-9]{3,}", orig_stem))
    sugg_tokens = set(re.findall(r"[a-z0-9]{3,}", sugg_stem))

    other_tokens = set()
    for o in other_files:
        if o.lower() != original_name.lower():
            other_tokens.update(re.findall(r"[a-z0-9]{3,}", Path(o).stem.lower()))

    # If the suggestion borrows a distinct token from another file in the batch,
    # and that token is NOT in the original filename, reject the hallucination
    borrowed = (sugg_tokens & other_tokens) - orig_tokens
    if borrowed:
        return False

    # For installers, software identity must be preserved
    ext = orig_path.suffix.lower()
    if ext in (".exe", ".msi", ".msix", ".dmg", ".deb", ".appimage", ".pkg"):
        orig_alpha = set(re.findall(r"[a-z]{3,}", orig_stem))
        sugg_alpha = set(re.findall(r"[a-z]{3,}", sugg_stem))
        if orig_alpha and sugg_alpha:
            has_overlap = any(s in orig_stem or o in sugg_stem for s in sugg_alpha for o in orig_alpha)
            if not has_overlap:
                return False

    return True
```

If the model hallucinates a name borrowed from another file in the folder, the safety guard catches it and safely falls back to standardizing the original filename.

### 4. Resilient JSON Parsing
Ollama's `format="json"` enforces valid JSON, but small models vary between returning an unkeyed list `[...]`, wrapping it in `{"files": [...]}`, or enclosing it in Markdown code blocks. `parse_llm_json` recursively inspects dict keys and values, validates through Pydantic, and gracefully degrades to extension rules if the daemon is offline.

### 5. Automated Unit Test Suite
The project includes a complete test suite with **12 unit tests** running in **0.37s** via `pytest`:
- Scanner filtering & content snippet extraction
- Fast-hash duplicate detection
- Algorithmic hallucination guard (`is_safe_rename`)
- JSON parsing flexibility across raw arrays, dict wrappers, and Markdown fences
- Collision resolution (`-1`, `-2`) and end-to-end atomic undo rollback

---

## Why Does Open Innovation Matter?

This project highlights exactly why open-source AI and local models are fundamentally better suited for personal desktop tools than closed commercial APIs:

1. **🔒 Absolute Privacy:** Your Downloads folder holds sensitive personal records — tax drafts, medical test PDFs, pay stubs, and password exports. Sending those filenames and content snippets across the internet to a third-party server is a major privacy compromise. With open-weight models in Ollama, **not a single byte leaves your localhost**.
2. **💸 Zero Marginal Cost:** Cloud APIs charge per token. Running an LLM across 1,000 files spread across your machine would cost real money every time. With local models, you set it up once and run it thousands of times for free.
3. **✈️ Truly Offline:** SlothSort works in airplane mode, on a train, or at a remote cabin with no internet connection.
4. **🎛️ Model Portability & User Freedom:** You are never locked into a single proprietary vendor. If you are on an ultra-light laptop, run `--model llama3.2:1b` or `--model phi3`. If you have a GPU, run `--model mistral` or `--model llama3.2`. 
5. **🛡️ Graceful Degradation:** If the local model service is not running or a file exceeds 500 MB, SlothSort doesn't crash with a `500 Server Error`. It seamlessly drops into deterministic rule-based sorting.

---

## The Lazy Payoff

International Sloth Day celebrates conserving energy and avoiding unnecessary effort.

Before building SlothSort, cleaning a bloated 800+ file Downloads folder meant sitting down, opening folders side-by-side, inspecting documents, and renaming files manually — usually taking 45 minutes of tedious drag-and-drop.

With SlothSort:
- **One command:** `slothsort ~/Downloads --execute --dedupe` categorizes and cleans up the entire directory in ~5 seconds.
- **The ultimate lazy workflow:** Run `slothsort ~/Downloads --watch --interval 60` in the background. As you download files throughout the week, SlothSort continuously files them into their proper category subfolders while you do literally anything else.

---

## Prize Categories

- **Slow and Steady (Primary Category):** Rewards laziness by eliminating one of the most common, dreaded computer chores with local open-weight AI.
- **Open-Source AI / Local Inference:** Runs 100% locally with open-weight models via Ollama.

---

*Sloths survive in the wild by moving deliberately and conserving energy. Let local open-source AI handle the busywork so you can take a nap.* 🦥
