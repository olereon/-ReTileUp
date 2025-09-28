#!/usr/bin/env python3.11
"""Comprehensive test runner for ReTileUp.

This script provides various test execution modes:
- Full test suite with coverage
- Quick smoke tests
- Performance tests
- Specific test categories
- Coverage validation and reporting
"""

import argparse
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import time
import shutil

PROJECT_ROOT = Path(__file__).parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
SRC_DIR = PROJECT_ROOT / "src"
COVERAGE_DIR = PROJECT_ROOT / "htmlcov"


class TestRunner:
    """Test runner for ReTileUp with comprehensive reporting."""

    def __init__(self, verbose: bool = False, parallel: bool = False):
        self.verbose = verbose
        self.parallel = parallel
        self.results = {}

    def run_command(self, cmd: List[str], description: str) -> Dict[str, Any]:
        """Run a command and capture results."""
        if self.verbose:
            print(f"Running: {description}")
            print(f"Command: {' '.join(cmd)}")

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            end_time = time.time()
            duration = end_time - start_time

            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': duration,
                'description': description
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timed out after 10 minutes',
                'duration': 600,
                'description': description
            }

        except Exception as e:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': 0,
                'description': description
            }

    def run_smoke_tests(self) -> bool:
        """Run quick smoke tests."""
        print("🔥 Running smoke tests...")

        cmd = [
            "python3.11", "-m", "pytest",
            "-m", "smoke",
            "--tb=short",
            "-v"
        ]

        if self.parallel:
            cmd.extend(["-n", "auto"])

        result = self.run_command(cmd, "Smoke tests")
        self.results['smoke'] = result

        if result['success']:
            print("✅ Smoke tests passed!")
        else:
            print("❌ Smoke tests failed!")
            if self.verbose:
                print(result['stderr'])

        return result['success']

    def run_unit_tests(self) -> bool:
        """Run unit tests with coverage."""
        print("🧪 Running unit tests...")

        cmd = [
            "python3.11", "-m", "pytest",
            "tests/unit/",
            "--cov=src/retileup",
            "--cov-report=term-missing",
            "--cov-branch",
            "-v"
        ]

        if self.parallel:
            cmd.extend(["-n", "auto"])

        result = self.run_command(cmd, "Unit tests")
        self.results['unit'] = result

        if result['success']:
            print("✅ Unit tests passed!")
        else:
            print("❌ Unit tests failed!")
            if self.verbose:
                print(result['stderr'])

        return result['success']

    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        print("🔗 Running integration tests...")

        cmd = [
            "python3.11", "-m", "pytest",
            "tests/integration/",
            "--tb=short",
            "-v"
        ]

        if self.parallel:
            cmd.extend(["-n", "auto"])

        result = self.run_command(cmd, "Integration tests")
        self.results['integration'] = result

        if result['success']:
            print("✅ Integration tests passed!")
        else:
            print("❌ Integration tests failed!")
            if self.verbose:
                print(result['stderr'])

        return result['success']

    def run_performance_tests(self) -> bool:
        """Run performance tests."""
        print("⚡ Running performance tests...")

        cmd = [
            "python3.11", "-m", "pytest",
            "tests/performance/",
            "-m", "performance",
            "--tb=short",
            "-v",
            "--durations=0"
        ]

        result = self.run_command(cmd, "Performance tests")
        self.results['performance'] = result

        if result['success']:
            print("✅ Performance tests passed!")
        else:
            print("❌ Performance tests failed!")
            if self.verbose:
                print(result['stderr'])

        return result['success']

    def run_edge_case_tests(self) -> bool:
        """Run edge case tests."""
        print("🔍 Running edge case tests...")

        cmd = [
            "python3.11", "-m", "pytest",
            "tests/edge_cases/",
            "-m", "edge_case",
            "--tb=short",
            "-v"
        ]

        result = self.run_command(cmd, "Edge case tests")
        self.results['edge_cases'] = result

        if result['success']:
            print("✅ Edge case tests passed!")
        else:
            print("❌ Edge case tests failed!")
            if self.verbose:
                print(result['stderr'])

        return result['success']

    def run_full_test_suite(self) -> bool:
        """Run the complete test suite with coverage."""
        print("🎯 Running full test suite with coverage...")

        cmd = [
            "python3.11", "-m", "pytest",
            "--cov=src/retileup",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-report=term-missing",
            "--cov-report=json:coverage.json",
            "--cov-branch",
            "--cov-fail-under=90",
            "--durations=10",
            "-v"
        ]

        if self.parallel:
            cmd.extend(["-n", "auto"])

        result = self.run_command(cmd, "Full test suite")
        self.results['full_suite'] = result

        if result['success']:
            print("✅ Full test suite passed!")
            self.analyze_coverage()
        else:
            print("❌ Full test suite failed!")
            if self.verbose:
                print(result['stderr'])

        return result['success']

    def analyze_coverage(self):
        """Analyze and report coverage statistics."""
        print("\n📊 Coverage Analysis:")

        # Read coverage JSON report
        coverage_json = PROJECT_ROOT / "coverage.json"
        if coverage_json.exists():
            try:
                with open(coverage_json) as f:
                    coverage_data = json.load(f)

                totals = coverage_data.get('totals', {})
                coverage_percent = totals.get('percent_covered', 0)

                print(f"Overall Coverage: {coverage_percent:.2f}%")

                if coverage_percent >= 90:
                    print("🎉 Coverage requirement met (≥90%)!")
                else:
                    print(f"⚠️  Coverage below requirement: {coverage_percent:.2f}% < 90%")

                # File-level coverage
                files = coverage_data.get('files', {})
                low_coverage_files = []

                for file_path, file_data in files.items():
                    file_coverage = file_data['summary']['percent_covered']
                    if file_coverage < 80:  # Flag files with low coverage
                        low_coverage_files.append((file_path, file_coverage))

                if low_coverage_files:
                    print("\n📉 Files with coverage < 80%:")
                    for file_path, coverage in sorted(low_coverage_files, key=lambda x: x[1]):
                        print(f"  {file_path}: {coverage:.1f}%")

                # Branch coverage
                if 'percent_covered_display' in totals:
                    branch_coverage = totals.get('percent_covered_display', 'N/A')
                    print(f"Branch Coverage: {branch_coverage}")

            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️  Could not parse coverage report: {e}")

        # Coverage report location
        if COVERAGE_DIR.exists():
            print(f"\n📄 HTML Coverage Report: {COVERAGE_DIR / 'index.html'}")

    def run_security_tests(self) -> bool:
        """Run security-focused tests."""
        print("🔒 Running security tests...")

        cmd = [
            "python3.11", "-m", "pytest",
            "-m", "security",
            "--tb=short",
            "-v"
        ]

        result = self.run_command(cmd, "Security tests")
        self.results['security'] = result

        if result['success']:
            print("✅ Security tests passed!")
        else:
            print("❌ Security tests failed!")
            if self.verbose:
                print(result['stderr'])

        return result['success']

    def validate_test_structure(self) -> bool:
        """Validate test structure and completeness."""
        print("🏗️  Validating test structure...")

        issues = []

        # Check for required test directories
        required_dirs = [
            TESTS_DIR / "unit",
            TESTS_DIR / "integration",
            TESTS_DIR / "performance",
            TESTS_DIR / "edge_cases",
            TESTS_DIR / "fixtures"
        ]

        for test_dir in required_dirs:
            if not test_dir.exists():
                issues.append(f"Missing test directory: {test_dir}")

        # Check for conftest.py
        conftest_file = TESTS_DIR / "conftest.py"
        if not conftest_file.exists():
            issues.append("Missing conftest.py in tests directory")

        # Check that source modules have corresponding tests
        src_modules = list((SRC_DIR / "retileup").rglob("*.py"))
        test_files = list(TESTS_DIR.rglob("test_*.py"))

        if len(test_files) < 10:  # Expect at least 10 test files
            issues.append(f"Only {len(test_files)} test files found, expected more comprehensive coverage")

        # Check for pytest configuration
        pytest_ini = PROJECT_ROOT / "pytest.ini"
        coveragerc = PROJECT_ROOT / ".coveragerc"

        if not pytest_ini.exists():
            issues.append("Missing pytest.ini configuration")

        if not coveragerc.exists():
            issues.append("Missing .coveragerc configuration")

        if issues:
            print("❌ Test structure validation failed:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("✅ Test structure validation passed!")
            return True

    def clean_coverage_files(self):
        """Clean up coverage files and reports."""
        print("🧹 Cleaning coverage files...")

        files_to_clean = [
            PROJECT_ROOT / ".coverage",
            PROJECT_ROOT / "coverage.xml",
            PROJECT_ROOT / "coverage.json",
            PROJECT_ROOT / "tests.log"
        ]

        dirs_to_clean = [
            COVERAGE_DIR,
            PROJECT_ROOT / ".pytest_cache"
        ]

        for file_path in files_to_clean:
            if file_path.exists():
                file_path.unlink()
                if self.verbose:
                    print(f"  Removed: {file_path}")

        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                if self.verbose:
                    print(f"  Removed: {dir_path}")

    def generate_test_report(self):
        """Generate a comprehensive test report."""
        print("\n📋 Test Report Summary:")
        print("=" * 50)

        total_duration = sum(result.get('duration', 0) for result in self.results.values())
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result.get('success', False))

        print(f"Total Test Suites: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Total Duration: {total_duration:.2f} seconds")

        print("\nDetailed Results:")
        for test_name, result in self.results.items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            duration = result.get('duration', 0)
            print(f"  {test_name}: {status} ({duration:.2f}s)")

        # Save detailed report
        report_file = PROJECT_ROOT / "test_report.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n📄 Detailed report saved to: {report_file}")


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="ReTileUp Test Runner")

    parser.add_argument(
        "mode",
        choices=["smoke", "unit", "integration", "performance", "edge", "security", "full", "validate", "clean"],
        help="Test mode to run"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "-p", "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )

    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=90.0,
        help="Coverage threshold (default: 90.0)"
    )

    args = parser.parse_args()

    runner = TestRunner(verbose=args.verbose, parallel=args.parallel)

    print(f"🚀 ReTileUp Test Runner - Mode: {args.mode}")
    print("=" * 50)

    success = True

    if args.mode == "smoke":
        success = runner.run_smoke_tests()
    elif args.mode == "unit":
        success = runner.run_unit_tests()
    elif args.mode == "integration":
        success = runner.run_integration_tests()
    elif args.mode == "performance":
        success = runner.run_performance_tests()
    elif args.mode == "edge":
        success = runner.run_edge_case_tests()
    elif args.mode == "security":
        success = runner.run_security_tests()
    elif args.mode == "full":
        structure_valid = runner.validate_test_structure()
        if structure_valid:
            success = runner.run_full_test_suite()
        else:
            success = False
    elif args.mode == "validate":
        success = runner.validate_test_structure()
    elif args.mode == "clean":
        runner.clean_coverage_files()
        print("✅ Cleanup completed!")
        return 0

    runner.generate_test_report()

    if success:
        print("\n🎉 All tests completed successfully!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())