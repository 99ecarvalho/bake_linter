# -*- coding: utf-8 -*-
"""
Base class for all lint rules.

This module provides the abstract base class that all lint rules must inherit from.
Rules register themselves automatically with the registry upon class definition.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import List, Dict, Any, Optional, ClassVar, Set

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.core.registry import get_registry


class RuleMeta(ABCMeta):
    """
    Metaclass that automatically registers rules with the registry.
    
    Inherits from ABCMeta to combine automatic rule registration with
    abstract base class functionality.
    
    Any class inheriting from BaseRule (that defines rule_id) will be
    automatically registered when the class is defined.
    """
    
    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> type:
        cls = super().__new__(mcs, name, bases, namespace)
        
        # Don't register the base class itself
        if name != "BaseRule" and hasattr(cls, "rule_id") and cls.rule_id:
            registry = get_registry()
            registry.register(cls)
        
        return cls


class BaseRule(metaclass=RuleMeta):
    """
    Abstract base class for all lint rules.
    
    To create a new rule:
    1. Create a new class inheriting from BaseRule
    2. Set the required class attributes (rule_id, name, description)
    3. Implement the check() method
    4. The rule will be automatically registered
    
    Example:
        class MyCustomRule(BaseRule):
            rule_id = "CUSTOM001"
            name = "My Custom Check"
            description = "Checks for something specific"
            default_severity = Severity.WARNING
            groups = ["custom", "style"]
            
            def check(self, context: FileContext) -> List[LintResult]:
                results = []
                # ... check logic ...
                return results
    
    Class Attributes:
        rule_id: Unique identifier for the rule (e.g., "LICENSE001")
        name: Human-readable name for the rule
        description: Detailed description of what the rule checks
        default_severity: Default severity level for issues found
        enabled_by_default: Whether the rule is enabled by default
        groups: List of groups/categories this rule belongs to
        hint: Default hint for how to fix issues found by this rule
        applicable_file_types: File types this rule applies to
    """
    
    # Required class attributes (must be overridden)
    rule_id: ClassVar[str] = ""
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    
    # Optional class attributes (can be overridden)
    default_severity: ClassVar[Severity] = Severity.ERROR
    enabled_by_default: ClassVar[bool] = True
    groups: ClassVar[List[str]] = []
    hint: ClassVar[Optional[str]] = None
    applicable_file_types: ClassVar[Set[str]] = {"recipe", "bbappend", "include"}
    
    def __init__(
        self,
        severity_override: Optional[Severity] = None,
        options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a rule instance.
        
        Args:
            severity_override: Override the default severity
            options: Rule-specific configuration options
        """
        self._severity = severity_override or self.default_severity
        self._options = options or {}

    @property
    def severity(self) -> Severity:
        """Get the effective severity for this rule."""
        return self._severity

    def get_option(self, key: str, default: Any = None) -> Any:
        """Get a rule-specific configuration option."""
        return self._options.get(key, default)

    def is_applicable(self, context: FileContext) -> bool:
        """
        Check if this rule should be applied to the given file.
        
        Override this method to add custom applicability logic.
        
        Args:
            context: The file context to check
            
        Returns:
            True if the rule should be applied
        """
        return context.file_type in self.applicable_file_types

    @abstractmethod
    def check(self, context: FileContext) -> List[LintResult]:
        """
        Check a file for issues.
        
        This is the main method that implements the rule's logic.
        It receives a parsed FileContext and returns a list of
        LintResult objects for any issues found.
        
        Args:
            context: Parsed file context to check
            
        Returns:
            List of LintResult objects (empty if no issues)
        """
        pass

    def create_result(
        self,
        file: Any,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        hint: Optional[str] = None,
        context: Optional[str] = None,
        severity: Optional[Severity] = None,
    ) -> LintResult:
        """
        Helper method to create a LintResult with this rule's info.
        
        Args:
            file: The file path
            message: Description of the issue
            line: Line number (1-indexed)
            column: Column number (1-indexed)
            hint: How to fix the issue (defaults to rule's hint)
            context: Code snippet or additional context
            severity: Override severity for this specific result
            
        Returns:
            A LintResult object
        """
        return LintResult(
            rule_id=self.rule_id,
            file=file,
            line=line,
            column=column,
            severity=severity or self._severity,
            message=message,
            hint=hint or self.hint,
            context=context,
            rule_name=self.name,
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.rule_id})>"
