"""Tests for content learning (Gap 8)."""

import pytest
from lib.content_learner import ContentLearner, learn_from_edit_event


@pytest.fixture
def learner():
    """Create a fresh ContentLearner for each test."""
    cl = ContentLearner()
    cl.state = {"patterns_seen": {}, "files_analyzed": 0, "last_project": None}
    return cl


class TestPythonPatterns:
    """Test Python code pattern detection."""

    def test_snake_case_functions(self, learner):
        code = '''
def my_function():
    pass

def another_func():
    return True
'''
        patterns = learner.learn_from_code(code, "test.py")
        assert ("naming_style", "snake_case") in patterns

    def test_type_hints(self, learner):
        code = '''
def greet(name: str) -> str:
    return f"Hello {name}"
'''
        patterns = learner.learn_from_code(code, "test.py")
        assert ("typing", "type_hints") in patterns

    def test_f_strings(self, learner):
        code = '''
name = "world"
msg = f"Hello {name}!"
'''
        patterns = learner.learn_from_code(code, "test.py")
        assert ("string_style", "f_strings") in patterns

    def test_broad_except(self, learner):
        code = '''
try:
    risky()
except Exception as e:
    log(e)
'''
        patterns = learner.learn_from_code(code, "test.py")
        assert ("error_handling", "broad_except") in patterns

    def test_specific_except(self, learner):
        code = '''
try:
    risky()
except ValueError:
    handle_value_error()
'''
        patterns = learner.learn_from_code(code, "test.py")
        assert ("error_handling", "specific_except") in patterns

    def test_dataclasses(self, learner):
        code = '''
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int
'''
        patterns = learner.learn_from_code(code, "test.py")
        assert ("data_modeling", "dataclasses") in patterns

    def test_pathlib(self, learner):
        code = '''
from pathlib import Path
file = Path("test.txt")
'''
        patterns = learner.learn_from_code(code, "test.py")
        assert ("path_handling", "pathlib") in patterns


class TestJavaScriptPatterns:
    """Test JavaScript/TypeScript pattern detection."""

    def test_arrow_functions(self, learner):
        code = '''
const greet = (name) => {
    return `Hello ${name}`;
};
'''
        patterns = learner.learn_from_code(code, "test.js")
        assert ("function_style", "arrow_functions") in patterns

    def test_async_await(self, learner):
        code = '''
async function fetchData() {
    const data = await fetch(url);
    return data;
}
'''
        patterns = learner.learn_from_code(code, "test.js")
        assert ("async_style", "async_await") in patterns

    def test_promise_chains(self, learner):
        code = '''
fetch(url)
    .then(response => response.json())
    .then(data => console.log(data));
'''
        patterns = learner.learn_from_code(code, "test.js")
        assert ("async_style", "promise_chains") in patterns

    def test_react_hooks(self, learner):
        code = '''
import { useState, useEffect } from 'react';

function Counter() {
    const [count, setCount] = useState(0);
    useEffect(() => {
        document.title = `Count: ${count}`;
    }, [count]);
}
'''
        patterns = learner.learn_from_code(code, "test.tsx")
        assert ("react_patterns", "hooks") in patterns
        assert ("react_patterns", "effects") in patterns


class TestGenericPatterns:
    """Test language-agnostic pattern detection."""

    def test_todo_comments(self, learner):
        code = '''
function process() {
    // TODO: implement this
    return null;
}
'''
        patterns = learner.learn_from_code(code, "test.js")
        assert ("comments", "todo_markers") in patterns

    def test_tabs_indentation(self, learner):
        code = "function test() {\n\treturn true;\n}"
        patterns = learner.learn_from_code(code, "test.js")
        assert ("indentation", "tabs") in patterns

    def test_spaces_indentation(self, learner):
        code = "def test():\n    return True\n"
        patterns = learner.learn_from_code(code, "test.py")
        assert ("indentation", "4_spaces") in patterns


class TestProjectStructure:
    """Test project structure learning."""

    def test_separate_tests_dir(self, learner):
        files = ["src/main.py", "tests/test_main.py", "tests/test_utils.py"]
        conventions = learner.learn_from_project_structure(files)
        assert conventions.get("test_organization") == "separate_tests_dir"

    def test_jest_style_tests(self, learner):
        files = ["src/App.tsx", "src/__tests__/App.test.tsx"]
        conventions = learner.learn_from_project_structure(files)
        assert conventions.get("test_organization") == "jest_style"

    def test_colocated_tests(self, learner):
        files = ["src/utils.ts", "src/utils.test.ts"]
        conventions = learner.learn_from_project_structure(files)
        assert conventions.get("test_organization") == "colocated_tests"

    def test_src_directory(self, learner):
        files = ["project/src/main.py", "project/src/utils.py"]
        conventions = learner.learn_from_project_structure(files)
        assert conventions.get("source_organization") == "src_directory"

    def test_typescript_detection(self, learner):
        files = ["src/main.ts", "tsconfig.json"]
        conventions = learner.learn_from_project_structure(files)
        assert conventions.get("typescript") == "configured"

    def test_eslint_detection(self, learner):
        files = ["src/main.js", ".eslintrc.json"]
        conventions = learner.learn_from_project_structure(files)
        assert conventions.get("linting") == "eslint"


class TestPatternAccumulation:
    """Test that patterns accumulate and trigger insight storage."""

    def test_pattern_counting(self, learner):
        code = "def my_func():\n    pass\n"

        # First occurrence
        learner.learn_from_code(code, "a.py")
        assert learner.state["patterns_seen"].get("naming_style:snake_case") == 1

        # Second occurrence
        learner.learn_from_code(code, "b.py")
        assert learner.state["patterns_seen"].get("naming_style:snake_case") == 2

    def test_files_analyzed_counter(self, learner):
        assert learner.state["files_analyzed"] == 0
        learner.learn_from_code("def test_function():\n    return True\n", "a.py")
        assert learner.state["files_analyzed"] == 1
        learner.learn_from_code("def another_function():\n    return False\n", "b.py")
        assert learner.state["files_analyzed"] == 2

    def test_stats(self, learner):
        learner.learn_from_code("def my_func():\n    return True\n", "a.py")
        learner.learn_from_code("def my_func():\n    return True\n", "b.py")

        stats = learner.get_stats()
        assert stats["files_analyzed"] == 2
        assert stats["unique_patterns"] > 0


class TestEdgeCase:
    """Test edge cases."""

    def test_empty_code(self, learner):
        patterns = learner.learn_from_code("", "test.py")
        assert patterns == []

    def test_short_code(self, learner):
        patterns = learner.learn_from_code("x=1", "test.py")
        assert patterns == []

    def test_unknown_extension(self, learner):
        patterns = learner.learn_from_code("some content here with tabs\t", "test.xyz")
        # Should still detect generic patterns
        assert ("indentation", "tabs") in patterns

    def test_empty_files_list(self, learner):
        conventions = learner.learn_from_project_structure([])
        assert conventions == {}


def test_convenience_function():
    """Test the learn_from_edit_event convenience function."""
    patterns = learn_from_edit_event("test.py", "def my_function():\n    return True\n")
    assert len(patterns) > 0
