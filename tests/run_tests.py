"""
Test Runner for ResearchPilot AI Reliability Test Suite
Reports passing and failing tests separately with timing and status details.
"""
import unittest
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.test_reliability import TestResearchReliability
from tests.test_ui_vfs import TestStreamlitUIVfs


class DetailedTestResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.passed_tests = []
        self.failed_tests = []
        self.error_tests = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_tests.append(test._testMethodName)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.failed_tests.append((test._testMethodName, err))

    def addError(self, test, err):
        super().addError(test, err)
        self.error_tests.append((test._testMethodName, err))


def run_and_report():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestResearchReliability))
    suite.addTests(loader.loadTestsFromTestCase(TestStreamlitUIVfs))
    result = DetailedTestResult()

    print("=" * 65)
    print("  ResearchPilot AI — Research Reliability & Quality Test Suite")
    print("=" * 65)

    suite.run(result)

    print(f"\n✅ PASSING TESTS ({len(result.passed_tests)}):")
    for t in result.passed_tests:
        print(f"  [PASS] {t}")

    print(f"\n❌ FAILING TESTS ({len(result.failed_tests) + len(result.error_tests)}):")
    if not result.failed_tests and not result.error_tests:
        print("  None. All tests passed successfully!")
    else:
        for t, err in result.failed_tests:
            print(f"  [FAIL] {t}")
        for t, err in result.error_tests:
            print(f"  [ERROR] {t}")

    print("\n" + "=" * 65)
    print(f"  Total: {result.testsRun} | Passed: {len(result.passed_tests)} | Failed: {len(result.failed_tests)} | Errors: {len(result.error_tests)}")
    print("=" * 65)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_and_report())
