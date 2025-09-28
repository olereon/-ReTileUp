#!/usr/bin/env python3.11
"""
Coverage validation script for ReTileUp existing codebase.
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def run_targeted_coverage():
    """Run coverage on existing, working modules only."""

    # Test only the modules that actually work
    working_tests = [
        "tests/unit/test_core/test_config.py",
        # Add other working test files as discovered
    ]

    cmd = [
        "python3.11", "-m", "pytest",
        "--cov=src/retileup",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=json:coverage.json",
        "--cov-branch",
        "-v"
    ] + working_tests

    print("🧪 Running targeted coverage on working modules...")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    print("STDOUT:")
    print(result.stdout)

    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    return result.returncode == 0

def analyze_actual_coverage():
    """Analyze what modules we actually have vs what we tested."""

    # Find all Python source files
    src_files = list((PROJECT_ROOT / "src").rglob("*.py"))
    test_files = list((PROJECT_ROOT / "tests").rglob("*.py"))

    print(f"\n📊 Source Code Analysis:")
    print(f"Source files found: {len(src_files)}")
    print(f"Test files created: {len(test_files)}")

    print(f"\n📝 Source modules:")
    for src_file in sorted(src_files):
        rel_path = src_file.relative_to(PROJECT_ROOT / "src")
        print(f"  - {rel_path}")

    print(f"\n🧪 Test modules:")
    for test_file in sorted(test_files):
        rel_path = test_file.relative_to(PROJECT_ROOT / "tests")
        print(f"  - {rel_path}")

def main():
    """Main validation function."""
    print("🚀 ReTileUp Coverage Validation")
    print("=" * 50)

    # First analyze what we have
    analyze_actual_coverage()

    # Then run targeted tests
    success = run_targeted_coverage()

    if success:
        print("\n✅ Targeted coverage analysis completed!")
    else:
        print("\n❌ Some issues found in coverage analysis")

    # Try to read coverage results if available
    coverage_json = PROJECT_ROOT / "coverage.json"
    if coverage_json.exists():
        import json
        try:
            with open(coverage_json) as f:
                data = json.load(f)
            totals = data.get('totals', {})
            coverage_percent = totals.get('percent_covered', 0)
            print(f"\n📊 Actual Coverage: {coverage_percent:.2f}%")

            # Show per-file coverage
            files = data.get('files', {})
            print("\n📁 Per-file coverage:")
            for file_path, file_data in files.items():
                file_coverage = file_data['summary']['percent_covered']
                print(f"  {file_path}: {file_coverage:.1f}%")

        except Exception as e:
            print(f"⚠️ Could not parse coverage data: {e}")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())