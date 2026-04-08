# Professional Test Runner Guide

## Overview

The WaseemBrain project includes a professional test runner that executes all tests in a single command with comprehensive reporting.

## Quick Start

```bash
# Run all tests (recommended)
python run_all_professional.py

# Or using npm
npm test
```

## Commands

### Basic Commands

| Command | Description |
|---------|-------------|
| `python run_all_professional.py` | Run all tests with default settings |
| `python run_all_professional.py --verbose` | Run with verbose output |
| `python run_all_professional.py --failfast` | Stop on first failure |
| `python run_all_professional.py --coverage` | Enable coverage reporting |

### NPM Scripts

```bash
npm test                    # Run professional test suite
npm run test:prof           # Run professional test suite
npm run test:prof:verbose  # Verbose mode
npm run test:prof:failfast  # Stop on first failure
npm run test:py             # Run pytest directly
npm run test:coverage       # Run with coverage
```

## Test Categories

The test runner organizes tests into categories:

| Category | Files Covered |
|----------|---------------|
| **types** | Type definitions, branded strings |
| **config** | Configuration loading, parsing |
| **normalizer** | Input normalization (PDF, text, voice, URL) |
| **memory** | Memory graph, SQLite operations |
| **experts** | Expert pool, registry, inference |
| **router** | Router clients (artifact, daemon, hybrid) |
| **learning** | Response policy learning |
| **components** | Full system integration |
| **integration** | End-to-end integration tests |
| **runtime** | Runtime service tests |
| **quality** | Quality gate checks |
| **reasoning** | Reasoning enhancement |
| **bootstrap** | Bootstrap and initialization |

## Output Format

### Console Output

```
================================================================================
WASEEM BRAIN - PROFESSIONAL TEST SUITE
================================================================================
Started: 2026-04-06 13:00:00

Discovering test files...
Found 25 test files

[1/25] Running test_types.py... ✓ PASS (3p/0f) [0.5s]
[2/25] Running test_normalizer.py... ✓ PASS (6p/0f) [1.2s]
...

================================================================================
TEST EXECUTION SUMMARY
================================================================================
Total Files:     25
Total Tests:     85
Passed:          85 (100.0%)
Failed:          0
Duration:        12.34 seconds

BY CATEGORY:
--------------------------------------------------------------------------------
bootstrap         | Files:   2 | Tests:   5 | Passed:   5 | Failed:  0 | Rate: 100.0% | Time:   2.10s
components       | Files:   1 | Tests:  13 | Passed:  13 | Failed:  0 | Rate: 100.0% | Time:   3.50s
integration      | Files:   3 | Tests:  10 | Passed:  10 | Failed:  0 | Rate: 100.0% | Time:   4.20s
...

================================================================================
Report saved to: tests/python/test_report_professional.json
================================================================================
```

### JSON Report

A detailed JSON report is saved to `tests/python/test_report_professional.json`:

```json
{
  "summary": {
    "total_files": 25,
    "total_tests": 85,
    "passed": 85,
    "failed": 0,
    "pass_rate": 100.0,
    "duration_seconds": 12.34
  },
  "categories": {
    "types": {
      "files": 2,
      "tests": 8,
      "passed": 8,
      "failed": 0,
      "duration": 2.5
    }
  },
  "files": [
    {
      "path": "tests/python/test_types.py",
      "name": "test_types.py",
      "category": "types",
      "tests": 3,
      "passed": 3,
      "failed": 0,
      "duration": 0.5,
      "status": "PASS"
    }
  ]
}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python run_all_professional.py
      - uses: actions/upload-artifact@v3
        with:
          name: test-report
          path: tests/python/test_report_professional.json
```

### Jenkins Example

```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh 'python run_all_professional.py'
                archiveArtifacts artifacts: 'tests/python/test_report_professional.json'
            }
        }
    }
}
```

## Advanced Usage

### Custom Test Discovery

To add custom test categories, edit `run_all_professional.py`:

```python
categories = {
    "my_category": ["test_my_feature*.py"],
}
```

### Parallel Execution

For large test suites, consider using pytest-xdist:

```bash
py -3.11 -m pytest tests/python -n auto
```

### HTML Coverage Report

```bash
python run_all_professional.py --coverage
open htmlcov/index.html
```

## Troubleshooting

### Tests Not Found

Ensure you're in the project root directory:

```bash
cd "d:\latest brain"
python run_all_professional.py
```

### Import Errors

Install dependencies:

```bash
pip install -r requirements.txt
```

### Permission Denied

Make the script executable (Linux/Mac):

```bash
chmod +x run_all_professional.py
```

## Performance

| Test Count | Expected Duration |
|-------------|-------------------|
| 50 tests    | ~5-10 seconds |
| 100 tests   | ~15-25 seconds |
| 500 tests   | ~60-90 seconds |
| 1000 tests  | ~120-180 seconds |

## Best Practices

1. Run tests before committing code
2. Use `--failfast` during development for quick feedback
3. Use `--verbose` when debugging specific failures
4. Review JSON reports for detailed analysis
5. Keep test files under 5 minutes each
6. Use category-based organization for large projects
