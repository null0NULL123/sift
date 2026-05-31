"""Test runner - discovers and runs all test modules.

Usage:
    python tests/runner.py                # run all tests
    python tests/runner.py storage        # run only storage tests
    python tests/runner.py config models  # run config and models tests
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# Test modules in execution order
MODULES = [
    "test_config",
    "test_models",
    "test_storage",
    "test_sources",
    "test_pipeline",
    "test_summarizer",
    "test_channels",
]


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: list[str] = []

    def run_test(self, name: str, fn) -> None:
        try:
            fn()
            print(f"  ✓ {name}")
            self.passed += 1
        except AssertionError as e:
            import traceback
            print(f"  ✗ {name}: {e}")
            traceback.print_exc()
            self.failed += 1
            self.errors.append(f"{name}: {e}")
        except Exception as e:
            import traceback
            print(f"  ✗ {name}: EXCEPTION {type(e).__name__}: {e}")
            traceback.print_exc()
            self.failed += 1
            self.errors.append(f"{name}: {type(e).__name__}: {e}")

    def run_module(self, mod_name: str) -> None:
        short_name = mod_name.replace("test_", "")
        try:
            mod = importlib.import_module(mod_name)
        except ImportError as e:
            print(f"\n  ✗ {mod_name}: import failed - {e}")
            self.failed += 1
            self.errors.append(f"{mod_name}: import failed - {e}")
            return

        tests = getattr(mod, "TESTS", None)
        if tests is None:
            print(f"\n  ⚠ {mod_name}: no TESTS list found, skipping")
            return

        print(f"\n{'='*50}")
        print(f"  {short_name}")
        print(f"{'='*50}")
        for name, fn in tests:
            self.run_test(name, fn)

    def run(self, filters: set[str] | None = None) -> bool:
        print("Sift Test Suite")
        print("=" * 50)

        for mod_name in MODULES:
            short_name = mod_name.replace("test_", "")
            if filters and short_name not in filters and mod_name not in filters:
                continue
            self.run_module(mod_name)

        print(f"\n{'='*50}")
        print(f"  Results: {self.passed} passed, {self.failed} failed")
        print(f"{'='*50}")

        if self.errors:
            print("\nFailures:")
            for e in self.errors:
                print(f"  - {e}")
            return False

        print("\nAll tests passed ✓")
        return True


def main():
    filters = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    runner = TestRunner()
    success = runner.run(filters)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
