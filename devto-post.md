---
title: "I Built an Offline AI File Organizer Because My Downloads Folder Was Ruining My Life"
published: true
description: "A fast, local CLI tool using Ollama + Llama 3.2 that sorts messy folders and renames files contextually. Zero cloud APIs, zero recurring costs, with instant rollback."
tags: opensource, ai, python, devchallenge
cover_image: 
---

Last week I needed to find a health insurance reimbursement receipt from three months ago. 

I opened my `Downloads` folder, typed "receipt" into the search bar, and was greeted with 847 unorganized files. Among them were four different versions of `scan0001 (1).pdf`, three files named `docker-compose (2).yml`, and dozens of camera uploads with names like `IMG_20241019_142356.jpg`.

Like most developers, I've written quick bash scripts in the past to tidy up folders:

```bash
mv *.pdf ~/Documents/
mv *.png ~/Images/
```

That works for about thirty seconds until you realize:
1. `meeting_notes.txt`, `quick_scratch.py`, and `todo.md` all get dumped into random buckets or left behind.
2. A photo named `IMG_20241019_142356.jpg` is still completely unsearchable two months later.
3. If a file is named `final_report_v2_EDITED_FINAL.docx`, moving it into a folder called `Documents/` doesn't make the filename any less chaotic.

With International Sloth Day here and this week's theme being **Slow and Steady** (building things that reward laziness and automate tasks you dread), I wanted a tool that actually understands what a file is, renames it properly, and sorts it without me lifting a finger.

So I built **[slothsort](https://github.com/slothsort/slothsort)**.

---

## What It Does

`slothsort` is a local command-line tool. You point it at any messy directory, and it analyzes your files using an open-weight model running on your machine via **Ollama**.

It does four things:
1. **Contextual classification:** Identifies the category not just by extension, but by reading filename tokens and peeking at the first few lines of text-based files.
2. **Standardized renaming:** Turns messy names like `Screenshot 2026-10-21 000814.png` or `IMG_20241019_142356.jpg` into clean, human-readable kebab-case filenames (`screenshot-2026-10-21-000814.png`, `photo-2024-10-19.jpg`).
3. **Safe execution with rollback:** Runs in dry-run mode by default, shows a clean terminal diff, and maintains an atomic undo log so you can reverse everything in one command.
4. **True Sloth Mode (`--watch`):** Channeling the International Sloth Day spirit, `--watch` runs continuously in the background, tidying up new downloads automatically while you take a nap.
5. **Cryptographic Deduplication (`--dedupe`):** Catches identical file downloads (`invoice (1).pdf`) with fast SHA-256 matching and isolates them into `Duplicates/`.

Here is what the terminal output looks like:

```text
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

## Why Open-Source AI Matters Here

I could have wired this up to GPT-4o or Claude in fifteen minutes. But for a desktop utility, relying on proprietary cloud APIs would have made the tool worse in almost every practical way.

### 1. File names leak sensitive personal data
Look at what lives in your Downloads folder:
- `tax_return_2024_draft.pdf`
- `blood_test_results_august.pdf`
- `resignation_letter.docx`
- `bank_statement_checking.csv`

Pumping those filenames and content snippets across the internet to a third-party server is a non-starter. With open-weight models (like `llama3.2` or `mistral`) running inside Ollama, **not a single packet leaves your machine**. You can run it on a laptop in airplane mode with Wi-Fi disabled and it works identically.

### 2. Nobody wants to pay API bills to clean their desktop
If you have 1,200 files scattered across your machine, sending batches of file metadata and receiving structured JSON responses through commercial cloud APIs costs real money. Local models have zero marginal cost. You can run `slothsort` every hour on a cron job without thinking about token counts.

### 3. Model portability
Because the interface communicates with Ollama's local endpoint, users can swap models based on their hardware with a single flag:
- On lightweight laptops: `--model phi3` or `--model llama3.2:1b`
- On machines with dedicated GPUs: `--model llama3.2` or `--model mistral`

---

## Technical Challenges & What I Learned

Building with local small language models (SLMs) taught me several lessons that don't show up in tutorials:

### 1. The Cross-Contamination Hallucination Trap
During testing on a real Downloads folder, I hit a fascinating bug with Llama 3.2 3B. 

I gave the model a batch of 9 files that included both `ABDownloadManager_1.11.1_windows_x64.exe` and `bitdefender_windows_....exe`. Because smaller models process all batch items in one context window, Llama 3.2 had a moment of confusion: it suggested renaming `ABDownloadManager` to `bitdefender.exe`!

If an automated tool silently renames one software package to the name of another software package, that's catastrophic.

To solve this, I built an algorithmic **Safety Guard** (`is_safe_rename`) in Python:
```python
def is_safe_rename(original_name: str, suggested_name: str, other_files: list[str]) -> bool:
    orig_tokens = set(re.findall(r"[a-z0-9]{3,}", Path(original_name).stem.lower()))
    sugg_tokens = set(re.findall(r"[a-z0-9]{3,}", Path(suggested_name).stem.lower()))

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

    return True
```
If the model suggests a name that borrows unique words from other files in the same batch, the safety guard catches it and falls back to a clean kebab-case format of the original file. The tool became genuinely bulletproof.

### 2. Pure filenames aren't enough (Content Peeking)
When I tested the first prototype, the model struggled with generic filenames like `notes.txt` or `export.csv`. It had no idea whether `notes.txt` was a bash cheat-sheet or meeting minutes.

To fix this without blowing through the model's context window, I added a content sniffing step in `scanner.py`. For small text, markdown, CSV, or code files (< 2MB), the scanner reads the first 300 characters, strips excessive whitespace, and passes it as a single-line hint:

```python
def extract_content_snippet(path: Path, max_chars: int = 300) -> str | None:
    if path.suffix.lower() not in TEXT_SNIPPET_EXTENSIONS:
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            chunk = f.read(max_chars).strip()
            return " ".join(chunk.split()) if chunk else None
    except Exception:
        return None
```

With that small snippet included in the batch prompt, the model correctly renamed `notes.txt` to `docker-swarm-setup-notes.txt` instead of making a blind guess.

### 3. Small models need flexible JSON parsing
Even when asking for JSON, local models sometimes return an unkeyed list `[...]` and other times wrap it in `{"files": [...]}` or `{"results": [...]}`. 

Instead of throwing a rigid error, `parse_llm_json` recursively inspects dict keys and values to extract whatever array the model returned, with automatic Pydantic validation.

### 4. Any tool that touches user files needs an undo button
A CLI script that silently moves and renames files without an easy rollback is terrifying.

Every time `slothsort --execute` runs, it writes an atomic manifest to `.slothsort-undo.json`:

```json
[
  {
    "from": "/home/user/Downloads/document(1).pdf",
    "to": "/home/user/Downloads/Documents/w2-tax-statement-2024.pdf"
  }
]
```

Running `slothsort undo ~/Downloads` reads that manifest in reverse order, puts every file back into its original path, resolves any naming collisions, and removes any empty category folders that were created.

---

## Try It Out

If you have Python 3.10+ and [Ollama](https://ollama.com/) installed:

```bash
# Pull a lightweight model
ollama pull llama3.2

# Clone and install
git clone https://github.com/slothsort/slothsort.git
cd slothsort
uv tool install .
# or: pip install -e .

# Run a test with dummy files
python demo/simulate_mess.py --target ./test_mess
slothsort ./test_mess
```

The repository with full documentation is available here:  
👉 **[GitHub: slothsort/slothsort](https://github.com/slothsort/slothsort)**

---

## Conclusion: Embrace the Sloth

Sloths survive in the wild not because they move fast, but because they are deliberate, calm, and refuse to waste energy on trivial things.

Your time is better spent building cool software, spending time with family, or taking a nap — not dragging `.pdf` files into folders one by one. Let open-source AI do the busywork.

Happy International Sloth Day! 🦥
