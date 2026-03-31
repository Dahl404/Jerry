# Dao Automated Testing & Bug Detection Framework

## Overview

This directory contains comprehensive automated testing and bug detection tools for the Dao codebase.

## Tools

### 1. Auto Bug Detector (`auto_bug_detector.py`)

A comprehensive static analysis and dynamic testing tool that automatically detects bugs, security vulnerabilities, and code quality issues.

#### Features

- **Static Code Analysis**
  - Undefined name detection
  - Unused import detection
  - Bare except clause detection
  - Hardcoded secrets detection
  - Dangerous function usage (eval, exec, etc.)
  - Path traversal vulnerability detection
  - Command injection detection
  - Resource leak detection
  - Type issue detection
  - Import issue detection
  - Cyclomatic complexity analysis
  - Error handling issues
  - Threading issues
  - Mutable default argument detection
  - Global variable usage detection
  - Assert statement detection

- **Security Scanning**
  - Insecure deserialization (pickle, marshal)
  - Weak cryptography detection
  - Insecure random number generation
  - Credential hardcoding

- **Dynamic Testing**
  - Syntax validation
  - Import testing
  - Runtime error detection

#### Usage

```bash
# Run on current directory
python3 tests/auto_bug_detector.py .

# Run on specific directory with custom output
python3 tests/auto_bug_detector.py /path/to/code -o report.md

# Run with help
python3 tests/auto_bug_detector.py --help
```

#### Output

Generates a detailed Markdown report (`bugs.md` by default) containing:
- Summary table by severity
- Category breakdown
- Detailed bug reports with:
  - Timestamp
  - Severity level (CRITICAL, HIGH, MEDIUM, LOW)
  - Category
  - CWE ID (where applicable)
  - Exact file location and line numbers
  - Code context/snippet
  - Impact description
  - Suggested fix
  - Confidence level
  - Tags

### 2. Unit Test Suite (`test_dao_core.py`)

Comprehensive unit tests for the dao_core modules.

#### Coverage

- **Config Module**: API URLs, model parameters, limits, tool definitions
- **Models Module**: LogEntry, ChatMsg, Todo, State classes
- **Worker Module**: Worker class, API calls, error handling
- **Executor Module**: All tool implementations
- **Agent Module**: Agent lifecycle, message injection
- **Edge Cases**: Boundary conditions, concurrent access

#### Usage

```bash
# Run all tests
python3 -m unittest tests.test_dao_core -v

# Run specific test class
python3 -m unittest tests.test_dao_core.TestModels -v

# Run specific test
python3 -m unittest tests.test_dao_core.TestModels.test_state_initialization -v
```

## Bug Severity Levels

| Level | Description | Action Required |
|-------|-------------|-----------------|
| **CRITICAL** | System-crashing bugs, syntax errors, import failures | Immediate fix required |
| **HIGH** | Runtime errors, security vulnerabilities, undefined names | Fix as soon as possible |
| **MEDIUM** | Code quality issues, potential bugs, maintainability concerns | Fix in next iteration |
| **LOW** | Style issues, minor improvements | Fix when convenient |

## Bug Categories

- **SECURITY**: Security vulnerabilities (injection, credentials, etc.)
- **LOGIC**: Logic errors, undefined variables, type issues
- **ERROR_HANDLING**: Missing or incorrect error handling
- **RESOURCE_LEAK**: File descriptor leaks, unclosed resources
- **MAINTAINABILITY**: Code structure, complexity, documentation
- **IMPORT**: Import-related issues
- **SYNTAX**: Syntax errors
- **CONCURRENCY**: Threading and concurrency issues

## Bug Report Format

The generated `bugs.md` file contains:

1. **Summary Section**
   - Total bugs found
   - Breakdown by severity
   - Breakdown by category

2. **Detailed Reports**
   Each bug includes:
   - Unique ID (e.g., BUG-001, DYN-001, SEC-001)
   - ISO 8601 timestamp
   - Severity and category
   - CWE ID (for security issues)
   - Precise location (file, line, column, function, class)
   - Code snippet with context
   - Description and impact
   - Suggested fix
   - Confidence level
   - Tags

## Integration

### Continuous Integration

Add to your CI pipeline:

```yaml
# Example GitHub Actions step
- name: Run Bug Detection
  run: |
    python3 tests/auto_bug_detector.py . -o bugs.md
    
- name: Upload Bug Report
  uses: actions/upload-artifact@v2
  with:
    name: bug-report
    path: bugs.md
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
python3 tests/auto_bug_detector.py . -o /tmp/bugs.md
if grep -q "CRITICAL" /tmp/bugs.md; then
    echo "Critical bugs found! Commit rejected."
    exit 1
fi
```

## Interpreting Results

### False Positives

Some findings may be false positives:
- Undefined names that are actually defined at runtime (dynamic imports)
- Unused imports that are used via `__all__` or for side effects
- Mutable defaults that are intentionally shared state

Review each finding in context before dismissing.

### Priority Matrix

Focus on bugs in this order:
1. CRITICAL + SECURITY
2. CRITICAL + LOGIC
3. HIGH + SECURITY
4. HIGH + LOGIC
5. MEDIUM + any category

## Example Findings

### Critical Bug Example
```markdown
### BUG-001: Undefined name 'LOG_LIMIT'

**Severity:** CRITICAL
**Location:** dao_core/models.py:67
**Impact:** Will cause NameError at runtime
**Fix:** Add `from .config import LOG_LIMIT`
```

### Security Vulnerability Example
```markdown
### SEC-003: Potential command injection

**Severity:** CRITICAL
**Location:** dao_core/executor.py:45
**CWE:** CWE-78
**Evidence:** subprocess.run(cmd, shell=True, ...)
**Fix:** Use shell=False and pass arguments as list
```

## Best Practices

1. **Run Regularly**: Run the bug detector after each significant change
2. **Fix Critical First**: Always address CRITICAL and HIGH severity bugs first
3. **Track Trends**: Monitor bug counts over time to ensure code quality improves
4. **Don't Ignore Warnings**: Even LOW severity bugs can indicate deeper issues
5. **Security First**: SECURITY category bugs should be reviewed immediately

## Limitations

- Static analysis cannot detect all runtime errors
- Some findings may be false positives
- Cannot detect logical errors in business logic
- Limited detection of race conditions
- Cannot detect performance issues without profiling

## Contributing

To add new bug detection rules:

1. Add a new `check_*` method to `StaticAnalyzer`
2. Use `_add_bug()` to report findings
3. Add tests for the new rule
4. Update this documentation

## Support

For questions or issues with the testing framework, check the main Dao documentation or file an issue.

---

**Last Updated:** 2026-03-07  
**Version:** 1.0.0
