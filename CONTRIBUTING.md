# Contributing to SlothSort

Thanks for your interest in improving SlothSort!

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/slothsort/slothsort.git
   cd slothsort
   ```

2. **Set up the virtual environment with `uv`:**
   ```bash
   uv sync
   ```

3. **Verify the CLI:**
   ```bash
   uv run slothsort --help
   ```

## Running Tests

### Unit Test Suite
Run the test suite using `pytest`:
```bash
uv run --with pytest pytest
```

### Sandbox Testing with Demo Suite
Use `demo/simulate_mess.py` to create and test against dummy directories:

```bash
# Generate dummy files
uv run python demo/simulate_mess.py --target test_mess

# Test dry run
uv run slothsort test_mess

# Test execution
uv run slothsort test_mess --execute

# Test rollback
uv run slothsort undo test_mess

# Clean up
rm -r test_mess
```

## Adding File Categories or Mappings

- Taxonomy categories and extensions live in `slothsort/config.py` in `DEFAULT_CATEGORIES` and `EXTENSION_MAP`.
- When adding new extensions, ensure they map to appropriate categories and that system clutter rules in `scanner.py` aren't affected.

## Code Standards

- Python 3.10+ type hints are required for all public functions.
- Keep terminal UI clean, minimalistic, and consistent with UNIX ergonomics.
- Ensure all file moves are logged in the undo manifest and collision-checked.
