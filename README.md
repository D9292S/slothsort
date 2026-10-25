# slothsort

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Runtime: Ollama](https://img.shields.io/badge/inference-Ollama-black.svg)](https://ollama.com/)
[![CLI: Rich](https://img.shields.io/badge/cli-Rich-magenta.svg)](https://github.com/Textualize/rich)

A local, deterministic file organizer that sorts and contextually renames files using open-weight models via Ollama. Runs 100% offline, never sends file metadata to external clouds, and features single-command atomic rollback.

```
$ slothsort ~/Downloads

Target:      /home/user/Downloads
Mode:        DRY-RUN (model: llama3.2)

  Category               Files            Size       Renamed        Inference  
  Images                     4          6.9 MB             1        1/4 local  
  Installers                 5        254.1 MB             3            rules  

Downloads/
├── Images/ (4)
│   ├── 1792294654173.jpg (standardized format (safety guarded))
│   ├── gog.jpg (standardized kebab-case)
│   ├── roadmap.gif (standardized kebab-case)
│   └── Screenshot 2026-10-21 000814.png → screenshot-2026-10-21-000814.png (standardized kebab-case)
└── Installers/ (5)
    ├── ABDownloadManager_1.11.1_windows_x64.exe → abdownloadmanager-1.11.1-windows-x64.exe (standardized kebab-case)
    ├── BatteryChecker_Setup_1.0.0.exe → batterychecker-setup-1.0.0.exe (standardized kebab-case)
    ├── bitdefender_windows_3e1ca47c-1dfc-479b-9861-c2104ebec328.exe → bitdefender-windows-3e1ca47c-1dfc-479b-9861-c2104ebec328.exe (standardized kebab-case)
    ├── iobituninstaller.exe (standardized kebab-case)
    └── python-manager-26.4.msix (standardized kebab-case)

Dry run complete. No files were modified on disk.
Run to apply: slothsort "/home/user/Downloads" --execute
```

---

## Table of Contents

- [Motivation](#motivation)
- [Why Open-Source AI?](#why-open-source-ai)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage & Examples](#usage--examples)
- [Command Reference](#command-reference)
- [Safety & Verification](#safety--verification)
- [Configuration (`.slothsort.toml`)](#configuration-slothsorttoml)
- [Architecture](#architecture)
- [Testing & Demos](#testing--demos)
- [License](#license)

---

## Motivation

Directory cleanup scripts usually take one of two bad paths:

1. **Naïve regex/extension scripts:** Group files solely by extension (`*.pdf` $\to$ `Documents/`). This fails because `notes.txt` could be a Python scratchpad or meeting notes, photos named `IMG_20241019_142356.jpg` remain unsearchable, and redundant noise (`document(3) final FINAL.docx`) stays cluttered.
2. **Cloud AI scripts:** Call commercial APIs (OpenAI, Anthropic). This sends sensitive personal filenames, tax records, invoices, and medical PDFs across the internet to third-party servers, while charging ongoing per-token API costs.

`slothsort` bridges this gap: it uses local open-weight models (like Meta's `llama3.2:3b` or `phi3`) running directly on your CPU or GPU through Ollama.

---

## Why Open-Source AI?

- 🔒 **Zero Data Leakage:** File paths and content headers stay on your machine. You can pull the network plug or run on an airplane; inference is completely local.
- 💸 **Zero Recurring Cost:** Organizing 50,000 files across different disks costs \$0.00.
- 🛡️ **Cross-Contamination Guard:** Includes algorithmic heuristics that prevent small 3B models from cross-pollinating names across files in a batch (e.g. preventing an installer from being renamed to a different software in the same folder).
- 🔄 **Deterministic Fallback:** If Ollama is offline or files exceed 500 MB, the system gracefully falls back to deterministic rule-based sorting without ever crashing.

---

## Prerequisites

1. **Python 3.10+**
2. **[Ollama](https://ollama.com/)** installed and running:
   ```bash
   # Pull the default lightweight model (3B parameters, ~2.0 GB)
   ollama pull llama3.2
   ```

---

## Installation

### With `uv` (Recommended)

To install globally into your shell path:
```bash
git clone https://github.com/slothsort/slothsort.git
cd slothsort
uv tool install .
```

To run directly without global installation:
```bash
uv run slothsort --help
```

### With `pip`
```bash
pip install -e .
```

---

## Usage & Examples

### 1. Dry Run (Preview only — safe by default)
```bash
slothsort ~/Downloads
```
Scans the directory, checks your local model, and outputs a formatted table and tree diff showing proposed changes without touching disk.

### 2. Apply Organization
```bash
slothsort ~/Downloads --execute
```
Moves files into category subdirectories, standardizes names, and records an atomic transaction manifest.

### 3. Interactive Confirmation Prompt
```bash
slothsort ~/Downloads --execute -i
```
Prompts `Move and rename N files? [y/N]` before applying filesystem modifications.

### 4. Categorize Without Renaming
```bash
slothsort ~/Downloads --execute --no-rename
```
Groups files into categorized folders (`Documents/`, `Images/`, `Code/`) while leaving original filenames intact.

### 5. Instant Rollback
```bash
slothsort undo ~/Downloads
```
Reads `.slothsort-undo.json`, restores all files to their original paths and names, and cleans up empty category folders.

---

## Command Reference

| Flag | Short | Description | Default |
| :--- | :---: | :--- | :---: |
| `--execute` | | Apply filesystem moves (disables dry-run) | `False` |
| `--interactive` | `-i` | Prompt for confirmation before applying changes | `False` |
| `--watch` | `-w` | Run continuously in background to organize incoming files | `False` |
| `--interval` | `-t` | Interval in seconds between watch cycles | `60` |
| `--dedupe` | | Identify duplicate files and isolate into `Duplicates/` | `False` |
| `--dest` | `-d` | Custom destination directory (instead of in-place) | Source dir |
| `--model` | `-m` | Local Ollama model tag | `llama3.2` |
| `--recursive` | `-r` | Traverse subdirectories recursively | `False` |
| `--no-rename` | | Disable AI rename suggestions, only categorize | `False` |
| `--peek / --no-peek` | | Inspect text file headers (< 2MB) for grounded context | `True` |
| `--config` | `-c` | Custom path to `.slothsort.toml` config file | Auto-detected |
| `--verbose` | `-v` | Display model inference and diagnostic logs | `False` |
| `--help` | | Show usage help | |

---

## Safety & Verification

`slothsort` is built around defensive file operations:

1. **Dry-Run by Default:** You must explicitly pass `--execute` to write changes.
2. **Collision Resolution:** If a target filename already exists in the destination folder, numeric suffixes (`-1`, `-2`) are appended. Existing files are never overwritten.
3. **Atomic Undo Manifest:** Real executions write a `.slothsort-undo.json` manifest. Running `slothsort undo <DIR>` reads this log in reverse order to restore previous state.
4. **Algorithmic Hallucination Guard (`is_safe_rename`):** Small local LLMs can occasionally borrow words from adjacent items in a batch. If the model suggests renaming `AppA.exe` to `AppB.exe` because `AppB.exe` was in the same batch, the safety guard catches the borrowed token and rejects the hallucination.
5. **Content Sniffing (< 2MB):** For ambiguous text files (`.txt`, `.csv`, `.json`, `.py`, `.md`), the scanner peeks at the first 300 characters to provide the model with grounding context before deciding categories.

---

## Configuration (`.slothsort.toml`)

You can customize `slothsort` behavior by placing a `.slothsort.toml` in the target folder, in your project root, or in `~/.config/slothsort/config.toml`:

```toml
# Default local model tag
model = "llama3.2"

# Files processed per model prompt
batch_size = 15

# Glob patterns to ignore during scanning
ignore = [
  "*.tmp",
  "*.crdownload",
  "*.part",
  "node_modules/*",
  ".git/*",
]
```

---

## Architecture

```
                       ┌─────────────────────────┐
                       │    Target Directory     │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │      Smart Scanner      │
                       │  • Filters system noise │
                       │  • Peeks text snippets  │
                       └────────────┬────────────┘
                                    │  (Batches of 15)
                                    ▼
                       ┌─────────────────────────┐
                       │    Local Ollama API     │
                       │  • llama3.2 (format=json)│
                       └────────────┬────────────┘
                                    │
                         ┌──────────┴──────────┐
                         │                     │
                  (Model available)     (Ollama offline)
                         │                     │
                         ▼                     ▼
              ┌─────────────────────┐┌─────────────────────┐
              │ JSON Parser         ││ Deterministic       │
              │ + Hallucination Guard││ Taxonomy Engine    │
              └──────────┬──────────┘└──────────┬──────────┘
                         │                      │
                         └──────────┬───────────┘
                                    ▼
                       ┌─────────────────────────┐
                       │   Conflict Resolution   │
                       │   (-1, -2 suffix check) │
                       └────────────┬────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
              [--dry-run]                     [--execute]
                     │                             │
                     ▼                             ▼
           ┌──────────────────┐          ┌──────────────────┐
           │ Rich Diff Tree & │          │ Atomic Moves +   │
           │ Summary Table    │          │ .slothsort-undo  │
           └──────────────────┘          └──────────────────┘
```

---

## Testing & Demos

### Automated Test Suite
Run the complete unit test suite covering scanner filters, duplicate hashing, LLM JSON parsing, rollback operations, and hallucination guards:

```bash
uv run --with pytest pytest
```

### Realistic Demo Sandbox
A test-bench generator is included to create realistic messy dummy files without touching your personal files:

```bash
# 1. Generate ~30 messy files in ./demo_folder
python demo/simulate_mess.py --target ./demo_folder

# 2. Preview
slothsort ./demo_folder

# 3. Execute
slothsort ./demo_folder --execute

# 4. Rollback
slothsort undo ./demo_folder
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
