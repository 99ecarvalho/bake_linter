# -*- coding: utf-8 -*-
"""
Rule registry for automatic rule discovery and management.

This module provides the infrastructure for registering lint rules
and discovering them automatically at runtime.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Type, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from bake_linter.rules.base import BaseRule


class RuleRegistry:
    """
    Central registry for all lint rules.
    
    Rules register themselves using the @register_rule decorator or
    by inheriting from BaseRule. The registry supports:
    
    - Automatic discovery of rules in the rules package
    - Rule lookup by ID
    - Rule filtering by group/category
    - Enabling/disabling rules dynamically
    
    Example:
        >>> registry = RuleRegistry()
        >>> registry.discover_rules()
        >>> rule = registry.get_rule("LICENSE001")
        >>> all_rules = registry.get_all_rules()
    """
    
    _instance: Optional["RuleRegistry"] = None
    _rules: Dict[str, Type["BaseRule"]] = {}
    _groups: Dict[str, Set[str]] = {}

    def __new__(cls) -> "RuleRegistry":
        """Singleton pattern for global registry access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rules = {}
            cls._instance._groups = {}
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the registry (mainly for testing)."""
        cls._instance = None
        cls._rules = {}
        cls._groups = {}

    def register(self, rule_class: Type["BaseRule"]) -> Type["BaseRule"]:
        """
        Register a rule class with the registry.
        
        Args:
            rule_class: The rule class to register
            
        Returns:
            The rule class (allows use as decorator)
            
        Raises:
            ValueError: If rule_id is already registered
        """
        rule_id = rule_class.rule_id
        
        if rule_id in self._rules:
            existing = self._rules[rule_id]
            if existing is not rule_class:
                raise ValueError(
                    f"Rule ID '{rule_id}' is already registered by {existing.__name__}"
                )
            return rule_class
        
        self._rules[rule_id] = rule_class
        
        # Register in groups
        for group in rule_class.groups:
            if group not in self._groups:
                self._groups[group] = set()
            self._groups[group].add(rule_id)
        
        return rule_class

    def get_rule(self, rule_id: str) -> Optional[Type["BaseRule"]]:
        """Get a rule class by its ID."""
        return self._rules.get(rule_id)

    def get_all_rules(self) -> Dict[str, Type["BaseRule"]]:
        """Get all registered rules."""
        return dict(self._rules)

    def get_rules_by_group(self, group: str) -> List[Type["BaseRule"]]:
        """Get all rules in a specific group."""
        rule_ids = self._groups.get(group, set())
        return [self._rules[rid] for rid in rule_ids if rid in self._rules]

    def get_all_groups(self) -> List[str]:
        """Get all registered group names."""
        return list(self._groups.keys())

    def get_rule_ids(self) -> List[str]:
        """Get all registered rule IDs."""
        return list(self._rules.keys())

    def discover_rules(self, package_name: str = "bake_linter.rules") -> int:
        """
        Discover and register all rules in the rules package.
        
        This method imports all modules in the rules package, which
        triggers their @register_rule decorators or BaseRule registration.
        
        Args:
            package_name: The package to scan for rules
            
        Returns:
            Number of rules discovered
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError as e:
            raise ImportError(f"Cannot import rules package '{package_name}': {e}")

        # Get the package path
        if hasattr(package, "__path__"):
            package_path = package.__path__
        else:
            return 0

        # Import all modules in the package
        for importer, modname, ispkg in pkgutil.walk_packages(
            package_path, prefix=f"{package_name}."
        ):
            if not modname.endswith(".base"):  # Skip base module
                try:
                    importlib.import_module(modname)
                except ImportError as e:
                    # Log but don't fail on import errors
                    print(f"Warning: Failed to import rule module {modname}: {e}")

        return len(self._rules)


# Global registry instance
_registry = RuleRegistry()


def register_rule(cls: Type["BaseRule"]) -> Type["BaseRule"]:
    """
    Decorator to register a rule class with the global registry.
    
    Example:
        @register_rule
        class MyRule(BaseRule):
            rule_id = "MY001"
            ...
    """
    return _registry.register(cls)


def get_registry() -> RuleRegistry:
    """Get the global rule registry instance."""
    return _registry
