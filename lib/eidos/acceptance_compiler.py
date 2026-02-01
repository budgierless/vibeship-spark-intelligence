"""
EIDOS Acceptance Compiler: Definition of Done

Converts goal + constraints + success_criteria into explicit acceptance tests.

RULE: If acceptance tests don't exist, you're not allowed to enter EXECUTE.
You stay in EXPLORE/PLAN until a validation plan exists.

This single add kills a ton of rabbit holes by forcing clarity before action.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import Episode, Phase


class AcceptanceType(Enum):
    """Types of acceptance tests."""
    AUTOMATED = "automated"     # Can be run automatically (test, lint, build)
    MANUAL = "manual"           # Requires human verification
    OUTPUT = "output"           # Check specific output/state
    BEHAVIOR = "behavior"       # Check behavior in scenario
    METRIC = "metric"           # Check numeric threshold


class AcceptanceStatus(Enum):
    """Status of an acceptance test."""
    PENDING = "pending"         # Not yet run
    PASSED = "passed"           # Test passed
    FAILED = "failed"           # Test failed
    SKIPPED = "skipped"         # Intentionally skipped
    BLOCKED = "blocked"         # Cannot run (dependency)


@dataclass
class AcceptanceTest:
    """A single acceptance test for validating success."""
    test_id: str
    description: str
    test_type: AcceptanceType
    verification_method: str    # How to verify (command, check, observation)

    # For automated tests
    command: Optional[str] = None
    expected_output: Optional[str] = None
    expected_exit_code: int = 0

    # For metric tests
    metric_name: Optional[str] = None
    metric_threshold: Optional[float] = None
    metric_operator: str = ">="  # >=, <=, ==, !=

    # Status tracking
    status: AcceptanceStatus = AcceptanceStatus.PENDING
    actual_output: Optional[str] = None
    run_at: Optional[float] = None
    evidence_ref: Optional[str] = None

    # Metadata
    priority: int = 1           # 1 = must pass, 2 = should pass, 3 = nice to have
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.test_id:
            self.test_id = self._generate_id()

    def _generate_id(self) -> str:
        key = f"{self.description[:30]}:{self.created_at}"
        return f"acc_{hashlib.md5(key.encode()).hexdigest()[:8]}"

    @property
    def is_critical(self) -> bool:
        """Is this a critical (must-pass) test?"""
        return self.priority == 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "description": self.description,
            "test_type": self.test_type.value,
            "verification_method": self.verification_method,
            "command": self.command,
            "expected_output": self.expected_output,
            "expected_exit_code": self.expected_exit_code,
            "metric_name": self.metric_name,
            "metric_threshold": self.metric_threshold,
            "metric_operator": self.metric_operator,
            "status": self.status.value,
            "actual_output": self.actual_output,
            "run_at": self.run_at,
            "evidence_ref": self.evidence_ref,
            "priority": self.priority,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AcceptanceTest":
        return cls(
            test_id=data["test_id"],
            description=data["description"],
            test_type=AcceptanceType(data["test_type"]),
            verification_method=data["verification_method"],
            command=data.get("command"),
            expected_output=data.get("expected_output"),
            expected_exit_code=data.get("expected_exit_code", 0),
            metric_name=data.get("metric_name"),
            metric_threshold=data.get("metric_threshold"),
            metric_operator=data.get("metric_operator", ">="),
            status=AcceptanceStatus(data.get("status", "pending")),
            actual_output=data.get("actual_output"),
            run_at=data.get("run_at"),
            evidence_ref=data.get("evidence_ref"),
            priority=data.get("priority", 1),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class AcceptancePlan:
    """A complete acceptance plan for an episode."""
    plan_id: str
    episode_id: str
    goal: str
    success_criteria: str

    # The compiled tests
    tests: List[AcceptanceTest] = field(default_factory=list)

    # Plan status
    is_complete: bool = False   # All critical tests defined
    is_approved: bool = False   # Ready to enter EXECUTE

    # Tracking
    created_at: float = field(default_factory=time.time)
    approved_at: Optional[float] = None

    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = f"plan_{self.episode_id[:8]}"

    @property
    def critical_tests(self) -> List[AcceptanceTest]:
        """Get all critical (must-pass) tests."""
        return [t for t in self.tests if t.is_critical]

    @property
    def all_critical_passed(self) -> bool:
        """Have all critical tests passed?"""
        critical = self.critical_tests
        if not critical:
            return False
        return all(t.status == AcceptanceStatus.PASSED for t in critical)

    @property
    def any_critical_failed(self) -> bool:
        """Have any critical tests failed?"""
        return any(t.status == AcceptanceStatus.FAILED for t in self.critical_tests)

    @property
    def pending_tests(self) -> List[AcceptanceTest]:
        """Get tests that haven't been run."""
        return [t for t in self.tests if t.status == AcceptanceStatus.PENDING]

    @property
    def progress(self) -> float:
        """Get completion progress (0-1)."""
        if not self.tests:
            return 0.0
        passed = len([t for t in self.tests if t.status == AcceptanceStatus.PASSED])
        return passed / len(self.tests)

    def can_enter_execute(self) -> Tuple[bool, str]:
        """Check if we can enter EXECUTE phase."""
        if not self.tests:
            return False, "No acceptance tests defined"
        if not self.critical_tests:
            return False, "No critical (must-pass) tests defined"
        if not self.is_approved:
            return False, "Acceptance plan not approved"
        return True, "Ready for execution"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "episode_id": self.episode_id,
            "goal": self.goal,
            "success_criteria": self.success_criteria,
            "tests": [t.to_dict() for t in self.tests],
            "is_complete": self.is_complete,
            "is_approved": self.is_approved,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AcceptancePlan":
        return cls(
            plan_id=data["plan_id"],
            episode_id=data["episode_id"],
            goal=data["goal"],
            success_criteria=data["success_criteria"],
            tests=[AcceptanceTest.from_dict(t) for t in data.get("tests", [])],
            is_complete=data.get("is_complete", False),
            is_approved=data.get("is_approved", False),
            created_at=data.get("created_at", time.time()),
            approved_at=data.get("approved_at"),
        )


class AcceptanceCompiler:
    """
    Compiles goals into acceptance tests.

    This is the "Definition of Done" compiler that prevents endless objectives
    by forcing explicit, verifiable success criteria.
    """

    def __init__(self):
        self.plans: Dict[str, AcceptancePlan] = {}
        self._load()

    def _get_plans_path(self) -> Path:
        return Path.home() / ".spark" / "acceptance_plans.json"

    def _load(self):
        """Load plans from disk."""
        try:
            path = self._get_plans_path()
            if path.exists():
                data = json.loads(path.read_text(encoding='utf-8'))
                self.plans = {k: AcceptancePlan.from_dict(v) for k, v in data.items()}
        except Exception:
            self.plans = {}

    def _save(self):
        """Save plans to disk."""
        try:
            path = self._get_plans_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.to_dict() for k, v in self.plans.items()}
            path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception:
            pass

    def compile_from_episode(self, episode: Episode) -> AcceptancePlan:
        """
        Compile an episode's goal into acceptance tests.

        Analyzes:
        - goal (what we're trying to achieve)
        - success_criteria (how we know we succeeded)
        - constraints (what we must respect)

        Returns an AcceptancePlan with generated tests.
        """
        plan = AcceptancePlan(
            plan_id="",
            episode_id=episode.episode_id,
            goal=episode.goal,
            success_criteria=episode.success_criteria,
        )

        # Generate tests from success criteria
        tests = self._parse_success_criteria(episode.success_criteria, episode.goal)
        plan.tests = tests

        # Check if complete
        plan.is_complete = len(plan.critical_tests) > 0

        self.plans[plan.plan_id] = plan
        self._save()
        return plan

    def _parse_success_criteria(self, criteria: str, goal: str) -> List[AcceptanceTest]:
        """
        Parse success criteria into acceptance tests.

        Looks for patterns like:
        - "X works" → behavior test
        - "X passes" → automated test
        - "X < N" → metric test
        - "user can X" → manual test
        """
        tests = []
        criteria_lower = criteria.lower()

        # Pattern: automated test indicators
        if any(word in criteria_lower for word in ['test', 'pass', 'build', 'lint', 'compile']):
            tests.append(AcceptanceTest(
                test_id="",
                description=f"Automated tests pass for: {goal[:50]}",
                test_type=AcceptanceType.AUTOMATED,
                verification_method="Run test suite",
                priority=1,
            ))

        # Pattern: behavior indicators
        if any(word in criteria_lower for word in ['works', 'functions', 'able to', 'can']):
            tests.append(AcceptanceTest(
                test_id="",
                description=f"Behavior verification: {criteria[:50]}",
                test_type=AcceptanceType.BEHAVIOR,
                verification_method="Verify stated behavior works",
                priority=1,
            ))

        # Pattern: output indicators
        if any(word in criteria_lower for word in ['output', 'returns', 'produces', 'generates']):
            tests.append(AcceptanceTest(
                test_id="",
                description=f"Output verification: {criteria[:50]}",
                test_type=AcceptanceType.OUTPUT,
                verification_method="Check output matches expectation",
                priority=1,
            ))

        # Pattern: metric indicators
        if any(word in criteria_lower for word in ['<', '>', '=', 'less than', 'greater than', 'at least']):
            tests.append(AcceptanceTest(
                test_id="",
                description=f"Metric check: {criteria[:50]}",
                test_type=AcceptanceType.METRIC,
                verification_method="Measure and compare to threshold",
                priority=2,
            ))

        # Default: at least one manual verification
        if not tests:
            tests.append(AcceptanceTest(
                test_id="",
                description=f"Manual verification: {criteria[:50]}",
                test_type=AcceptanceType.MANUAL,
                verification_method="Human verifies success criteria",
                priority=1,
            ))

        return tests

    def add_test(self, plan_id: str, test: AcceptanceTest):
        """Add a test to a plan."""
        if plan_id in self.plans:
            self.plans[plan_id].tests.append(test)
            self.plans[plan_id].is_complete = len(self.plans[plan_id].critical_tests) > 0
            self._save()

    def approve_plan(self, plan_id: str) -> Tuple[bool, str]:
        """Approve a plan for execution."""
        if plan_id not in self.plans:
            return False, "Plan not found"

        plan = self.plans[plan_id]

        if not plan.is_complete:
            return False, "Plan incomplete - no critical tests"

        if not plan.critical_tests:
            return False, "No critical tests defined"

        plan.is_approved = True
        plan.approved_at = time.time()
        self._save()
        return True, "Plan approved"

    def record_test_result(
        self,
        plan_id: str,
        test_id: str,
        status: AcceptanceStatus,
        actual_output: str = "",
        evidence_ref: str = ""
    ):
        """Record a test result."""
        if plan_id not in self.plans:
            return

        plan = self.plans[plan_id]
        for test in plan.tests:
            if test.test_id == test_id:
                test.status = status
                test.actual_output = actual_output
                test.run_at = time.time()
                test.evidence_ref = evidence_ref
                break

        self._save()

    def get_plan(self, episode_id: str) -> Optional[AcceptancePlan]:
        """Get plan for an episode."""
        for plan in self.plans.values():
            if plan.episode_id == episode_id:
                return plan
        return None

    def check_can_execute(self, episode_id: str) -> Tuple[bool, str]:
        """Check if episode can enter EXECUTE phase."""
        plan = self.get_plan(episode_id)
        if not plan:
            return False, "No acceptance plan exists - create plan first"
        return plan.can_enter_execute()


# Singleton
_acceptance_compiler = None


def get_acceptance_compiler() -> AcceptanceCompiler:
    """Get singleton acceptance compiler."""
    global _acceptance_compiler
    if _acceptance_compiler is None:
        _acceptance_compiler = AcceptanceCompiler()
    return _acceptance_compiler
