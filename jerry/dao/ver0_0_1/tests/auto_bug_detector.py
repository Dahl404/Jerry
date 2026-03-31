#!/usr/bin/env python3
"""
Automated Bug Detection and Testing Framework for Dao
Performs comprehensive static analysis, dynamic testing, and security scanning.
Generates detailed bug reports with timestamps, line numbers, and fix suggestions.
"""

import ast
import os
import sys
import re
import json
import time
import tempfile
import threading
import subprocess
import traceback
import importlib
import importlib.util
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
from collections import defaultdict
import unittest
from unittest.mock import Mock, patch, MagicMock
import io
import contextlib


# =============================================================================
# Bug Report Data Structures
# =============================================================================

@dataclass
class BugLocation:
    """Precise location of a bug in the codebase."""
    file: str
    line: int
    column: int = 0
    end_line: int = 0
    end_column: int = 0
    function: str = ""
    class_name: str = ""


@dataclass
class CodeSnippet:
    """Code context around the bug."""
    before: List[str]
    problematic: str
    after: List[str]


@dataclass
class Bug:
    """Comprehensive bug report structure."""
    id: str
    timestamp: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str  # SECURITY, LOGIC, PERFORMANCE, STYLE, MAINTAINABILITY
    title: str
    description: str
    location: BugLocation
    code_snippet: Optional[CodeSnippet] = None
    impact: str = ""
    reproduction_steps: List[str] = field(default_factory=list)
    suggested_fix: str = ""
    cwe_id: str = ""  # Common Weakness Enumeration
    evidence: str = ""
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    tags: List[str] = field(default_factory=list)


# =============================================================================
# Static Code Analyzer
# =============================================================================

class StaticAnalyzer:
    """Performs static analysis on Python source code."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.source = ""
        self.lines: List[str] = []
        self.tree: Optional[ast.AST] = None
        self.bugs: List[Bug] = []
        self.bug_counter = 0

    def load(self):
        """Load and parse the source file."""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            self.source = f.read()
        self.lines = self.source.splitlines(keepends=True)
        self.tree = ast.parse(self.source, filename=self.filepath)

    def _next_bug_id(self) -> str:
        """Generate next bug ID."""
        self.bug_counter += 1
        return f"BUG-{self.bug_counter:03d}"

    def _get_code_snippet(self, lineno: int, context: int = 3) -> CodeSnippet:
        """Extract code snippet with context around a line."""
        start = max(0, lineno - context - 1)
        end = min(len(self.lines), lineno + context)
        before = [self.lines[i].rstrip() for i in range(start, lineno - 1)]
        problematic = self.lines[lineno - 1].rstrip() if lineno <= len(self.lines) else ""
        after = [self.lines[i].rstrip() for i in range(lineno, end)]
        return CodeSnippet(before=before, problematic=problematic, after=after)

    def _add_bug(self, severity: str, category: str, title: str, description: str,
                 lineno: int, column: int = 0, function: str = "", class_name: str = "",
                 impact: str = "", suggested_fix: str = "", cwe_id: str = "",
                 evidence: str = "", confidence: str = "HIGH", tags: List[str] = None):
        """Add a bug to the list."""
        bug = Bug(
            id=self._next_bug_id(),
            timestamp=datetime.now().isoformat(),
            severity=severity,
            category=category,
            title=title,
            description=description,
            location=BugLocation(
                file=os.path.abspath(self.filepath),
                line=lineno,
                column=column,
                function=function,
                class_name=class_name
            ),
            code_snippet=self._get_code_snippet(lineno),
            impact=impact,
            suggested_fix=suggested_fix,
            cwe_id=cwe_id,
            evidence=evidence,
            confidence=confidence,
            tags=tags or []
        )
        self.bugs.append(bug)

    def analyze_all(self):
        """Run all static analysis checks."""
        self.check_undefined_names()
        self.check_unused_imports()
        self.check_bare_except()
        self.check_hardcoded_secrets()
        self.check_dangerous_functions()
        self.check_path_traversal()
        self.check_command_injection()
        self.check_resource_leaks()
        self.check_type_issues()
        self.check_import_issues()
        self.check_complexity()
        self.check_error_handling()
        self.check_threading_issues()
        self.check_missing_return()
        self.check_assert_statements()
        self.check_global_variables()
        self.check_mutable_defaults()
        return self.bugs

    def check_undefined_names(self):
        """Check for undefined variable names with proper import tracking (two-pass)."""
        
        # First pass: collect all definitions
        defined_classes = set()
        defined_functions = set()
        imported_names = set()
        
        class DefinitionCollector(ast.NodeVisitor):
            def __init__(self):
                self.module_classes = set()
                self.module_functions = set()
                self.imported = set()
                
            def visit_Import(self, node):
                for alias in node.names:
                    name = alias.asname or alias.name
                    self.imported.add(name)
                self.generic_visit(node)
                
            def visit_ImportFrom(self, node):
                if node.module:
                    for alias in node.names:
                        name = alias.asname or alias.name
                        self.imported.add(name)
                self.generic_visit(node)
                
            def visit_ClassDef(self, node):
                self.module_classes.add(node.name)
                self.generic_visit(node)
                
            def visit_FunctionDef(self, node):
                self.module_functions.add(node.name)
                self.generic_visit(node)
                
            visit_AsyncFunctionDef = visit_FunctionDef
        
        collector = DefinitionCollector()
        collector.visit(self.tree)
        
        # Second pass: check for undefined names
        class NameVisitor(ast.NodeVisitor):
            def __init__(self, analyzer, module_classes, module_functions, imported):
                self.analyzer = analyzer
                self.scope_stack = [set()]
                self.imported_names = imported.copy()
                self.imported_names.update(module_classes)
                self.imported_names.update(module_functions)
                
                # Add Python builtins
                self.builtins = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
                self.builtins.update(['__name__', '__file__', '__doc__', '__package__', 
                                     '__cached__', '__annotations__', '__builtins__'])

            def visit_FunctionDef(self, node):
                self.scope_stack.append(set())
                for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                    self.scope_stack[-1].add(arg.arg)
                if node.args.vararg:
                    self.scope_stack[-1].add(node.args.vararg.arg)
                if node.args.kwarg:
                    self.scope_stack[-1].add(node.args.kwarg.arg)
                self.scope_stack[-1].add(node.name)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)

            def visit_ClassDef(self, node):
                self.scope_stack.append(set())
                self.scope_stack[-1].add(node.name)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_Lambda(self, node):
                self.scope_stack.append(set())
                for arg in node.args.args:
                    self.scope_stack[-1].add(arg.arg)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_ListComp(self, node):
                self.scope_stack.append(set())
                for gen in node.generators:
                    self._extract_targets(gen.target, self.scope_stack[-1])
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_SetComp(self, node):
                self.visit_ListComp(node)

            def visit_DictComp(self, node):
                self.scope_stack.append(set())
                for gen in node.generators:
                    self._extract_targets(gen.target, self.scope_stack[-1])
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_GeneratorExp(self, node):
                """Handle generator expressions like (x for x in iterable)"""
                self.scope_stack.append(set())
                for gen in node.generators:
                    self._extract_targets(gen.target, self.scope_stack[-1])
                self.generic_visit(node)
                self.scope_stack.pop()
                
            def _extract_targets(self, target, scope_set):
                """Extract all names from a target (handles nested tuples)"""
                if isinstance(target, ast.Name):
                    scope_set.add(target.id)
                elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                    for elt in target.elts:
                        self._extract_targets(elt, scope_set)

            def visit_ExceptHandler(self, node):
                if node.name:
                    self.scope_stack[-1].add(node.name)
                self.generic_visit(node)

            def visit_For(self, node):
                if isinstance(node.target, ast.Name):
                    self.scope_stack[-1].add(node.target.id)
                self.generic_visit(node)

            def visit_NamedExpr(self, node):
                if isinstance(node.target, ast.Name):
                    self.scope_stack[-1].add(node.target.id)
                self.generic_visit(node)

            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    self.scope_stack[-1].add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    all_defined = set()
                    for scope in self.scope_stack:
                        all_defined.update(scope)
                    all_defined.update(self.imported_names)
                    all_defined.update(self.builtins)
                    
                    is_module_attr = any(node.id + '.' in name for name in self.imported_names)
                    
                    if node.id not in all_defined and not is_module_attr:
                        self.analyzer._add_bug(
                            severity="HIGH",
                            category="LOGIC",
                            title=f"Undefined name '{node.id}'",
                            description=f"The name '{node.id}' is used but not defined in this scope.",
                            lineno=node.lineno,
                            column=node.col_offset,
                            impact="Will cause NameError at runtime",
                            suggested_fix=f"Define '{node.id}' or import it from the appropriate module.",
                            cwe_id="CWE-381",
                            confidence="MEDIUM"
                        )
                self.generic_visit(node)

            def visit_Attribute(self, node):
                self.generic_visit(node)

        visitor = NameVisitor(self, collector.module_classes, collector.module_functions, collector.imported)
        visitor.visit(self.tree)

    def check_unused_imports(self):
        """Check for unused imports."""
        class ImportVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer
                self.imports = {}  # name -> (lineno, module)
                self.uses = set()

            def visit_Import(self, node):
                for alias in node.names:
                    name = alias.asname or alias.name
                    self.imports[name] = (node.lineno, alias.name)
                self.generic_visit(node)

            def visit_ImportFrom(self, node):
                for alias in node.names:
                    name = alias.asname or alias.name
                    self.imports[name] = (node.lineno, f"{node.module}.{alias.name}")
                self.generic_visit(node)

            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Load):
                    self.uses.add(node.id)
                self.generic_visit(node)

            def visit_Attribute(self, node):
                # Track attribute access
                if isinstance(node.value, ast.Name):
                    self.uses.add(node.value.id)
                self.generic_visit(node)

        visitor = ImportVisitor(self)
        visitor.visit(self.tree)

        for name, (lineno, module) in visitor.imports.items():
            if name not in visitor.uses and not name.startswith('_'):
                self._add_bug(
                    severity="LOW",
                    category="MAINTAINABILITY",
                    title=f"Unused import '{name}'",
                    description=f"Import '{module}' is never used.",
                    lineno=lineno,
                    impact="Wastes memory and may cause confusion",
                    suggested_fix=f"Remove the unused import: 'import {module}'",
                    confidence="HIGH"
                )

    def check_bare_except(self):
        """Check for bare except clauses."""
        class ExceptVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer

            def visit_ExceptHandler(self, node):
                if node.type is None:
                    self.analyzer._add_bug(
                        severity="MEDIUM",
                        category="ERROR_HANDLING",
                        title="Bare except clause",
                        description="Using bare 'except:' catches all exceptions including SystemExit and KeyboardInterrupt.",
                        lineno=node.lineno,
                        impact="May hide serious errors and make debugging difficult",
                        suggested_fix="Use 'except Exception:' or specify specific exception types",
                        cwe_id="CWE-391",
                        confidence="HIGH"
                    )
                self.generic_visit(node)

        visitor = ExceptVisitor(self)
        visitor.visit(self.tree)

    def check_hardcoded_secrets(self):
        """Check for hardcoded secrets and credentials."""
        patterns = [
            (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', 'password'),
            (r'(?i)(api_key|apikey|api-key)\s*=\s*["\'][^"\']+["\']', 'API key'),
            (r'(?i)(secret|token)\s*=\s*["\'][^"\']+["\']', 'secret/token'),
            (r'(?i)(aws_access|aws_secret)\s*=\s*["\'][^"\']+["\']', 'AWS credential'),
        ]

        for i, line in enumerate(self.lines, 1):
            for pattern, secret_type in patterns:
                if re.search(pattern, line):
                    # Skip if it's a default empty value or environment variable
                    if '=""' in line or "=''" in line or 'os.environ' in line or 'getenv' in line:
                        continue
                    self._add_bug(
                        severity="CRITICAL",
                        category="SECURITY",
                        title=f"Hardcoded {secret_type}",
                        description=f"Potential {secret_type} found in source code.",
                        lineno=i,
                        impact="Credentials in source code can be leaked through version control",
                        suggested_fix="Use environment variables or a secrets manager",
                        cwe_id="CWE-798",
                        evidence=line.strip(),
                        confidence="MEDIUM",
                        tags=["security", "credentials"]
                    )

    def check_dangerous_functions(self):
        """Check for use of dangerous functions."""
        dangerous = {
            'eval': ('CWE-95', 'HIGH'),
            'exec': ('CWE-95', 'HIGH'),
            'compile': ('CWE-95', 'HIGH'),
            '__import__': ('CWE-95', 'MEDIUM'),  # Lower severity - often used safely
            'open': (None, 'INFO'),  # Info only - file ops are often intentional
            'input': (None, 'INFO'),  # Info only - Python 3 input() is safe
        }

        class CallVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in dangerous:
                        cwe, severity = dangerous[func_name]
                        
                        # Skip info-level findings
                        if severity == 'INFO':
                            pass  # Don't report these
                        else:
                            # Check if it's a hardcoded safe import
                            is_safe_import = False
                            if func_name == '__import__':
                                # Check if argument is a safe hardcoded string
                                if node.args and isinstance(node.args[0], ast.Constant):
                                    safe_modules = ['datetime', 'os', 'sys', 'json', 're']
                                    if node.args[0].value in safe_modules:
                                        is_safe_import = True
                            
                            if not is_safe_import:
                                self.analyzer._add_bug(
                                    severity=severity,
                                    category="SECURITY",
                                    title=f"Use of dangerous function '{func_name}'",
                                    description=f"The function '{func_name}' can execute arbitrary code.",
                                    lineno=node.lineno,
                                    impact="Code injection vulnerability if user input is passed",
                                    suggested_fix=f"Avoid using {func_name}() with untrusted input",
                                    cwe_id=cwe or "",
                                    confidence="MEDIUM",
                                    tags=["security", "code-injection"]
                                )
                self.generic_visit(node)

        visitor = CallVisitor(self)
        visitor.visit(self.tree)

    def check_path_traversal(self):
        """Check for potential path traversal vulnerabilities."""
        for i, line in enumerate(self.lines, 1):
            # Check for file operations without path validation
            if re.search(r'\b(open|os\.path\.join|Path)\s*\([^)]*\+', line):
                if 'abspath' not in line and 'resolve' not in line and 'normpath' not in line:
                    self._add_bug(
                        severity="HIGH",
                        category="SECURITY",
                        title="Potential path traversal vulnerability",
                        description="File path constructed with string concatenation without validation.",
                        lineno=i,
                        impact="Attackers may access arbitrary files using ../ sequences",
                        suggested_fix="Use os.path.abspath() and validate paths are within allowed directory",
                        cwe_id="CWE-22",
                        evidence=line.strip(),
                        confidence="MEDIUM",
                        tags=["security", "path-traversal"]
                    )

    def check_command_injection(self):
        """Check for potential command injection vulnerabilities."""
        dangerous_patterns = [
            (r'subprocess\.(run|call|Popen)\s*\([^)]*shell\s*=\s*True', 'shell=True in subprocess'),
            (r'os\.system\s*\(', 'os.system()'),
            (r'os\.popen\s*\(', 'os.popen()'),
        ]

        for i, line in enumerate(self.lines, 1):
            for pattern, func_name in dangerous_patterns:
                if re.search(pattern, line):
                    # Check if user input might be involved
                    if '+' in line or 'format' in line or 'f"' in line or "f'" in line:
                        self._add_bug(
                            severity="CRITICAL",
                            category="SECURITY",
                            title=f"Potential command injection via {func_name}",
                            description="Shell command constructed with string interpolation.",
                            lineno=i,
                            impact="Arbitrary command execution if user input is included",
                            suggested_fix="Use subprocess with shell=False and pass arguments as list",
                            cwe_id="CWE-78",
                            evidence=line.strip(),
                            confidence="HIGH",
                            tags=["security", "command-injection"]
                        )

    def check_resource_leaks(self):
        """Check for potential resource leaks."""
        class ResourceVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer
                self.in_with = False

            def visit_With(self, node):
                old_in_with = self.in_with
                self.in_with = True
                self.generic_visit(node)
                self.in_with = old_in_with

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    if node.func.id == 'open' and not self.in_with:
                        self.analyzer._add_bug(
                            severity="MEDIUM",
                            category="RESOURCE_LEAK",
                            title="File opened without context manager",
                            description="File opened with open() outside a 'with' statement may not be closed properly.",
                            lineno=node.lineno,
                            impact="File descriptor leak, especially in loops",
                            suggested_fix="Use 'with open(...) as f:' pattern",
                            cwe_id="CWE-404",
                            confidence="HIGH",
                            tags=["resource-leak", "file-handling"]
                        )
                self.generic_visit(node)

        visitor = ResourceVisitor(self)
        visitor.visit(self.tree)

    def check_import_issues(self):
        """Check for import-related issues."""
        for i, line in enumerate(self.lines, 1):
            # Check for wildcard imports
            if re.search(r'from\s+\S+\s+import\s+\*', line):
                self._add_bug(
                    severity="MEDIUM",
                    category="MAINTAINABILITY",
                    title="Wildcard import",
                    description="Using 'from module import *' pollutes namespace and makes dependencies unclear.",
                    lineno=i,
                    impact="Namespace pollution, unclear dependencies, potential name conflicts",
                    suggested_fix="Import specific names: 'from module import name1, name2'",
                    confidence="HIGH"
                )

            # Check for circular import patterns
            if 'import' in line and os.path.basename(self.filepath).replace('.py', '') in line:
                self._add_bug(
                    severity="LOW",
                    category="MAINTAINABILITY",
                    title="Potential circular import",
                    description="Module appears to import itself or a related module.",
                    lineno=i,
                    impact="May cause ImportError at runtime",
                    suggested_fix="Restructure imports to avoid circular dependencies",
                    confidence="LOW"
                )

    def check_type_issues(self):
        """Check for type-related issues."""
        class TypeVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer

            def visit_Compare(self, node):
                # Check for identity comparison with literals
                if node.ops[0].__class__.__name__ in ('Is', 'IsNot'):
                    if isinstance(node.comparators[0], ast.Constant):
                        val = node.comparators[0].value
                        if val in (True, False, None, 0, 1, ""):
                            self.analyzer._add_bug(
                                severity="LOW",
                                category="LOGIC",
                                title=f"Identity comparison with {val}",
                                description="Using 'is' with literals. Use '==' for value comparison.",
                                lineno=node.lineno,
                                impact="May work but is not the intended semantics",
                                suggested_fix=f"Use '==' instead of 'is' for comparing with {val}",
                                confidence="HIGH"
                            )
                self.generic_visit(node)

        visitor = TypeVisitor(self)
        visitor.visit(self.tree)

    def check_complexity(self):
        """Check for overly complex functions."""
        class ComplexityVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer

            def visit_FunctionDef(self, node):
                # Count cyclomatic complexity (rough estimate)
                complexity = 1
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                         ast.With, ast.Assert, ast.comprehension)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1

                if complexity > 10:
                    self.analyzer._add_bug(
                        severity="LOW",
                        category="MAINTAINABILITY",
                        title=f"High complexity in '{node.name}'",
                        description=f"Function has cyclomatic complexity of {complexity} (recommended: ≤10).",
                        lineno=node.lineno,
                        impact="Difficult to test and maintain",
                        suggested_fix="Break down into smaller functions",
                        confidence="HIGH"
                    )
                self.generic_visit(node)

        visitor = ComplexityVisitor(self)
        visitor.visit(self.tree)

    def check_error_handling(self):
        """Check for error handling issues."""
        for i, line in enumerate(self.lines, 1):
            # Check for pass in except block
            if re.search(r'except.*:\s*pass\s*$', line):
                self._add_bug(
                    severity="MEDIUM",
                    category="ERROR_HANDLING",
                    title="Silent exception handling",
                    description="Exception caught and ignored with 'pass'.",
                    lineno=i,
                    impact="Errors are hidden, making debugging difficult",
                    suggested_fix="Log the exception or handle it appropriately",
                    cwe_id="CWE-391",
                    confidence="HIGH"
                )

    def check_threading_issues(self):
        """Check for potential threading issues."""
        for i, line in enumerate(self.lines, 1):
            # Check for thread creation without proper cleanup
            if 'threading.Thread' in line and 'daemon=True' not in line and 'join(' not in line:
                # Look ahead for join
                context = ''.join(self.lines[i-1:min(i+10, len(self.lines))])
                if '.join(' not in context:
                    self._add_bug(
                        severity="MEDIUM",
                        category="CONCURRENCY",
                        title="Thread may not be properly joined",
                        description="Thread created without daemon=True or subsequent join() call.",
                        lineno=i,
                        impact="May cause program to hang or resources to leak",
                        suggested_fix="Use daemon=True or ensure thread.join() is called",
                        confidence="MEDIUM",
                        tags=["threading", "concurrency"]
                    )

    def check_missing_return(self):
        """Check for functions that should return but don't."""
        class ReturnVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer

            def visit_FunctionDef(self, node):
                # Check if function has explicit return type annotation
                has_return_annotation = node.returns is not None
                
                # Check if function has return statements
                has_return = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child.value is not None:
                        has_return = True
                        break

                # If annotated to return something but has no return, flag it
                if has_return_annotation and not has_return:
                    # Check if it's not just returning None explicitly
                    pass  # This is a complex check, skip for now

                self.generic_visit(node)

        visitor = ReturnVisitor(self)
        visitor.visit(self.tree)

    def check_assert_statements(self):
        """Check for assert statements that might be optimized away."""
        for i, line in enumerate(self.lines, 1):
            if line.strip().startswith('assert '):
                self._add_bug(
                    severity="LOW",
                    category="ERROR_HANDLING",
                    title="Assert statement used",
                    description="Assert statements can be optimized away with python -O.",
                    lineno=i,
                    impact="Validation may be skipped in optimized mode",
                    suggested_fix="Use explicit if/raise for important validation",
                    confidence="HIGH",
                    tags=["assert", "validation"]
                )

    def check_global_variables(self):
        """Check for excessive use of global variables."""
        class GlobalVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer
                self.global_count = 0

            def visit_Global(self, node):
                self.global_count += 1
                self.analyzer._add_bug(
                    severity="MEDIUM",
                    category="MAINTAINABILITY",
                    title="Global variable declared",
                    description="Use of 'global' statement makes code harder to test and maintain.",
                    lineno=node.lineno,
                    impact="Tight coupling, difficult to test",
                    suggested_fix="Use class attributes or dependency injection",
                    confidence="HIGH",
                    tags=["global", "maintainability"]
                )
                self.generic_visit(node)

        visitor = GlobalVisitor(self)
        visitor.visit(self.tree)

    def check_mutable_defaults(self):
        """Check for mutable default arguments."""
        class DefaultVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer

            def visit_FunctionDef(self, node):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default is None:
                        continue
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        self.analyzer._add_bug(
                            severity="MEDIUM",
                            category="LOGIC",
                            title="Mutable default argument",
                            description="Mutable default arguments are shared across all calls.",
                            lineno=node.lineno,
                            impact="Unexpected behavior when modifying the default",
                            suggested_fix="Use None as default and create new instance inside function",
                            cwe_id="CWE-398",
                            confidence="HIGH",
                            tags=["mutable", "default-argument"]
                        )
                self.generic_visit(node)

            visit_AsyncFunctionDef = visit_FunctionDef

        visitor = DefaultVisitor(self)
        visitor.visit(self.tree)


# =============================================================================
# Dynamic Tester
# =============================================================================

class DynamicTester:
    """Performs dynamic testing by executing code."""

    def __init__(self, module_path: str):
        self.module_path = module_path
        self.module_name = os.path.basename(module_path).replace('.py', '')
        self.bugs: List[Bug] = []
        self.bug_counter = 0

    def _next_bug_id(self) -> str:
        self.bug_counter += 1
        return f"DYN-{self.bug_counter:03d}"

    def test_import(self) -> Optional[Bug]:
        """Test if module can be imported."""
        try:
            # Get the directory containing the module
            module_dir = os.path.dirname(os.path.abspath(self.module_path))
            parent_dir = os.path.dirname(module_dir)
            
            # Add parent directory to sys.path for relative imports
            sys.path.insert(0, parent_dir)
            sys.path.insert(0, module_dir)
            
            # Try importing as a module
            spec = importlib.util.spec_from_file_location(self.module_name, self.module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            
            # Clean up sys.path
            sys.path.remove(parent_dir)
            sys.path.remove(module_dir)
            
            return None
        except Exception as e:
            # Only report as bug if it's a real error, not just relative import issues
            error_msg = str(e)
            if "attempted relative import" in error_msg:
                # This is expected for package modules, don't report as bug
                return None
            
            return Bug(
                id=self._next_bug_id(),
                timestamp=datetime.now().isoformat(),
                severity="CRITICAL",
                category="IMPORT",
                title=f"Module import failed",
                description=f"Cannot import module: {e}",
                location=BugLocation(file=self.module_path, line=1),
                impact="Module cannot be used",
                suggested_fix=f"Fix import errors: {e}",
                evidence=traceback.format_exc(),
                confidence="HIGH"
            )

    def test_syntax(self) -> Optional[Bug]:
        """Test if module has valid syntax."""
        try:
            with open(self.module_path, 'r') as f:
                compile(f.read(), self.module_path, 'exec')
            return None
        except SyntaxError as e:
            return Bug(
                id=self._next_bug_id(),
                timestamp=datetime.now().isoformat(),
                severity="CRITICAL",
                category="SYNTAX",
                title="Syntax error",
                description=str(e),
                location=BugLocation(
                    file=self.module_path,
                    line=e.lineno or 1,
                    column=e.offset or 0
                ),
                impact="Code cannot be executed",
                suggested_fix=f"Fix syntax: {e}",
                confidence="HIGH"
            )

    def run_all_tests(self) -> List[Bug]:
        """Run all dynamic tests."""
        bugs = []

        # Test syntax
        bug = self.test_syntax()
        if bug:
            bugs.append(bug)

        # Test import
        bug = self.test_import()
        if bug:
            bugs.append(bug)

        return bugs


# =============================================================================
# Security Scanner
# =============================================================================

class SecurityScanner:
    """Scans for security vulnerabilities."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.source = ""
        self.bugs: List[Bug] = []

    def load(self):
        with open(self.filepath, 'r', encoding='utf-8') as f:
            self.source = f.read()

    def scan(self) -> List[Bug]:
        """Run security scans."""
        self.load()
        lines = self.source.splitlines()

        # Check for insecure deserialization
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(pickle|marshal|shelve)\.(load|loads|Unpickler)', line):
                self.bugs.append(Bug(
                    id=f"SEC-{len(self.bugs)+1:03d}",
                    timestamp=datetime.now().isoformat(),
                    severity="CRITICAL",
                    category="SECURITY",
                    title="Insecure deserialization",
                    description="Using pickle/marshal with untrusted data allows arbitrary code execution.",
                    location=BugLocation(file=os.path.abspath(self.filepath), line=i),
                    impact="Remote code execution",
                    suggested_fix="Use JSON or other safe serialization formats",
                    cwe_id="CWE-502",
                    evidence=line.strip(),
                    confidence="HIGH",
                    tags=["security", "deserialization"]
                ))

            # Check for weak cryptography
            if re.search(r'\b(MD5|SHA1|sha1|md5)\b', line) and 'hashlib' in line:
                if 'password' in ''.join(lines[max(0,i-5):i+5]).lower():
                    self.bugs.append(Bug(
                        id=f"SEC-{len(self.bugs)+1:03d}",
                        timestamp=datetime.now().isoformat(),
                        severity="HIGH",
                        category="SECURITY",
                        title="Weak cryptographic hash for password",
                        description="MD5/SHA1 are not suitable for password hashing.",
                        location=BugLocation(file=os.path.abspath(self.filepath), line=i),
                        impact="Passwords may be cracked easily",
                        suggested_fix="Use bcrypt, scrypt, or argon2 for password hashing",
                        cwe_id="CWE-328",
                        confidence="MEDIUM",
                        tags=["security", "cryptography"]
                    ))

            # Check for random module usage in security context
            if 'random.' in line and any(kw in line for kw in ['token', 'key', 'secret', 'password']):
                self.bugs.append(Bug(
                    id=f"SEC-{len(self.bugs)+1:03d}",
                    timestamp=datetime.now().isoformat(),
                    severity="HIGH",
                    category="SECURITY",
                    title="Insecure random number generation",
                    description="random module is not cryptographically secure.",
                    location=BugLocation(file=os.path.abspath(self.filepath), line=i),
                    impact="Predictable security tokens",
                    suggested_fix="Use secrets module for security-sensitive random values",
                    cwe_id="CWE-330",
                    evidence=line.strip(),
                    confidence="HIGH",
                    tags=["security", "randomness"]
                ))

        return self.bugs


# =============================================================================
# Bug Report Generator
# =============================================================================

class BugReportGenerator:
    """Generates comprehensive bug reports."""

    def __init__(self, output_file: str = "bugs.md"):
        self.output_file = output_file
        self.bugs: List[Bug] = []

    def add_bugs(self, bugs: List[Bug]):
        """Add bugs to the report."""
        self.bugs.extend(bugs)

    def generate(self):
        """Generate the bug report."""
        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        self.bugs.sort(key=lambda b: severity_order.get(b.severity, 5))

        report = []
        report.append("# Automated Bug Report")
        report.append("")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Total Bugs Found:** {len(self.bugs)}")
        report.append("")

        # Summary table
        report.append("## Summary")
        report.append("")
        report.append("| Severity | Count |")
        report.append("|----------|-------|")

        severity_counts = defaultdict(int)
        for bug in self.bugs:
            severity_counts[bug.severity] += 1

        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            count = severity_counts.get(severity, 0)
            report.append(f"| {severity} | {count} |")

        report.append(f"| **Total** | **{len(self.bugs)}** |")
        report.append("")

        # Category breakdown
        report.append("## Bugs by Category")
        report.append("")
        category_counts = defaultdict(int)
        for bug in self.bugs:
            category_counts[bug.category] += 1

        for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            report.append(f"- **{category}:** {count}")
        report.append("")

        # Detailed bugs
        report.append("## Detailed Bug Reports")
        report.append("")

        for bug in self.bugs:
            report.append(self._format_bug(bug))
            report.append("")

        # Write to file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))

        print(f"Bug report written to: {self.output_file}")

    def _format_bug(self, bug: Bug) -> str:
        """Format a single bug for the report."""
        lines = []
        lines.append(f"### {bug.id}: {bug.title}")
        lines.append("")
        lines.append(f"**Timestamp:** {bug.timestamp}")
        lines.append(f"**Severity:** {bug.severity}")
        lines.append(f"**Category:** {bug.category}")
        if bug.cwe_id:
            lines.append(f"**CWE:** {bug.cwe_id}")
        lines.append(f"**Confidence:** {bug.confidence}")
        lines.append("")

        lines.append("**Location:**")
        lines.append(f"- File: `{bug.location.file}`")
        lines.append(f"- Line: {bug.location.line}")
        if bug.location.column:
            lines.append(f"- Column: {bug.location.column}")
        if bug.location.function:
            lines.append(f"- Function: `{bug.location.function}`")
        if bug.location.class_name:
            lines.append(f"- Class: `{bug.location.class_name}`")
        lines.append("")

        lines.append("**Description:**")
        lines.append(bug.description)
        lines.append("")

        if bug.evidence:
            lines.append("**Evidence:**")
            lines.append(f"```")
            lines.append(bug.evidence[:500])  # Truncate long evidence
            lines.append(f"```")
            lines.append("")

        if bug.code_snippet:
            lines.append("**Code Context:**")
            lines.append("```python")
            if bug.code_snippet.before:
                for line in bug.code_snippet.before:
                    lines.append(f"  {line}")
            lines.append(f"> {bug.code_snippet.problematic}")
            if bug.code_snippet.after:
                for line in bug.code_snippet.after:
                    lines.append(f"  {line}")
            lines.append("```")
            lines.append("")

        lines.append("**Impact:**")
        lines.append(bug.impact)
        lines.append("")

        if bug.reproduction_steps:
            lines.append("**Reproduction Steps:**")
            for i, step in enumerate(bug.reproduction_steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        if bug.suggested_fix:
            lines.append("**Suggested Fix:**")
            lines.append(bug.suggested_fix)
            lines.append("")

        if bug.tags:
            lines.append("**Tags:** " + ", ".join(bug.tags))
            lines.append("")

        lines.append("---")
        lines.append("")

        return '\n'.join(lines)


# =============================================================================
# Main Audit Runner
# =============================================================================

def find_python_files(directory: str) -> List[str]:
    """Find all Python files in directory, excluding common non-source directories."""
    py_files = []
    
    # Directories to exclude from scanning
    EXCLUDE_DIRS = {
        '__pycache__', '.git', 'venv', 'env', '.venv', 'tests',
        'dep',  # deprecated code
        'dao_workspace',  # working copies
        'dao_poems',  # workspace copies
        'build', 'dist', '.eggs', '*.egg-info'
    }
    
    for root, dirs, files in os.walk(directory):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
        
        # Skip if we're in an excluded path
        if any(exclude in root for exclude in EXCLUDE_DIRS):
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                py_files.append(filepath)
    
    return py_files


def run_comprehensive_audit(directory: str, output_file: str = "bugs.md"):
    """Run comprehensive audit on all Python files in directory."""
    print(f"Starting comprehensive audit of: {directory}")
    print("=" * 60)

    py_files = find_python_files(directory)
    print(f"Found {len(py_files)} Python files to analyze")
    print("=" * 60)

    report_generator = BugReportGenerator(output_file)
    total_bugs = 0

    for filepath in py_files:
        print(f"\nAnalyzing: {filepath}")

        # Static analysis
        try:
            analyzer = StaticAnalyzer(filepath)
            analyzer.load()
            bugs = analyzer.analyze_all()
            report_generator.add_bugs(bugs)
            total_bugs += len(bugs)
            print(f"  Static analysis: {len(bugs)} issues found")
        except SyntaxError as e:
            print(f"  Syntax error: {e}")
            report_generator.add_bugs([Bug(
                id=f"SYN-{total_bugs+1:03d}",
                timestamp=datetime.now().isoformat(),
                severity="CRITICAL",
                category="SYNTAX",
                title="Syntax error",
                description=str(e),
                location=BugLocation(file=filepath, line=e.lineno or 1),
                impact="File cannot be parsed",
                confidence="HIGH"
            )])
            total_bugs += 1
        except Exception as e:
            print(f"  Error during static analysis: {e}")

        # Security scan
        try:
            scanner = SecurityScanner(filepath)
            bugs = scanner.scan()
            report_generator.add_bugs(bugs)
            total_bugs += len(bugs)
            print(f"  Security scan: {len(bugs)} issues found")
        except Exception as e:
            print(f"  Error during security scan: {e}")

        # Dynamic testing
        try:
            tester = DynamicTester(filepath)
            bugs = tester.run_all_tests()
            report_generator.add_bugs(bugs)
            if bugs:
                print(f"  Dynamic tests: {len(bugs)} issues found")
        except Exception as e:
            print(f"  Error during dynamic testing: {e}")

    print("\n" + "=" * 60)
    print(f"Audit complete. Total bugs found: {total_bugs}")

    # Generate report
    report_generator.generate()

    return total_bugs


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Automated Bug Detection for Dao')
    parser.add_argument('directory', nargs='?', default='.',
                       help='Directory to audit (default: current directory)')
    parser.add_argument('-o', '--output', default='bugs.md',
                       help='Output file for bug report (default: bugs.md)')

    args = parser.parse_args()

    bugs_found = run_comprehensive_audit(args.directory, args.output)
    sys.exit(0 if bugs_found == 0 else 1)
