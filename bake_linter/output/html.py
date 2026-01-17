"""
HTML output formatter for visual reports.

Generates a standalone HTML report with:
- Summary dashboard
- Per-file issue breakdown
- Color-coded severities
- Expandable sections
- How-to-fix hints
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, TextIO
from collections import defaultdict
import html

from bake_linter.core.models import LintResult, LintSummary, Severity
from bake_linter.output.base import BaseFormatter


class HtmlFormatter(BaseFormatter):
    """
    HTML formatter for visual reports.
    
    Generates a self-contained HTML file with embedded CSS and JavaScript
    for an interactive lint report.
    """

    def __init__(
        self,
        output: Optional[TextIO] = None,
        color: bool = True,  # Ignored (HTML always has styling)
        verbose: bool = False,
        title: str = "Bake Linter Report",
    ):
        super().__init__(output, color, verbose)
        self.title = title

    def format_results(self, results: List[LintResult], summary: LintSummary) -> str:
        """Generate HTML report."""
        # Group results by file
        by_file: Dict[Path, List[LintResult]] = defaultdict(list)
        for result in results:
            by_file[result.file].append(result)
        
        # Group results by rule
        by_rule: Dict[str, List[LintResult]] = defaultdict(list)
        for result in results:
            by_rule[result.rule_id].append(result)
        
        # Get rule category mapping from registry
        from bake_linter.core.registry import get_registry
        registry = get_registry()
        rule_categories = {}
        all_rules = registry.get_all_rules()
        for rule_id, rule_cls in all_rules.items():
            if hasattr(rule_cls, 'groups') and rule_cls.groups:
                # Use first group as primary category
                rule_categories[rule_id] = rule_cls.groups[0].upper()
            else:
                rule_categories[rule_id] = 'OTHER'
        
        return self._render_html(results, summary, by_file, by_rule, rule_categories)

    def _render_html(
        self,
        results: List[LintResult],
        summary: LintSummary,
        by_file: Dict[Path, List[LintResult]],
        by_rule: Dict[str, List[LintResult]],
        rule_categories: Dict[str, str],
    ) -> str:
        """Render the complete HTML document."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(self.title)}</title>
    {self._get_styles()}
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 {html.escape(self.title)}</h1>
            <p class="timestamp">Generated: {timestamp}</p>
        </header>
        
        {self._render_summary(summary)}
        
        <nav class="tabs">
            <button class="tab-btn active" data-tab="files">By File</button>
            <button class="tab-btn" data-tab="rules">By Rule</button>
        </nav>
        
        <div id="files" class="tab-content active">
            <div class="expand-controls">
                <button class="expand-btn" data-action="expand-all" data-target="files">▼ Expand All</button>
                <button class="expand-btn" data-action="collapse-all" data-target="files">▲ Collapse All</button>
            </div>
            {self._render_files_section(by_file)}
        </div>
        
        <div id="rules" class="tab-content">
            <div class="expand-controls">
                <button class="expand-btn" data-action="expand-level1" data-target="rules">▼ Expand Rules</button>
                <button class="expand-btn" data-action="expand-all" data-target="rules">▼▼ Expand All</button>
                <button class="expand-btn" data-action="collapse-level1" data-target="rules">▲ Collapse to Categories</button>
                <button class="expand-btn" data-action="collapse-all" data-target="rules">▲▲ Collapse All</button>
            </div>
            {self._render_rules_section(by_rule, by_file, rule_categories)}
        </div>
        
        <footer>
            <p>Bake Linter Report • {summary.total_issues} issue(s) in {summary.files_scanned} file(s)</p>
            <blockquote style="margin:2em 0 0 0;padding:1em 1.5em;background:#f8f9fa;border-left:5px solid #667eea;font-style:italic;color:#444;">
                <span style="font-size:1.1em;">“A linter this, that runs by hearth or hall,<br>
                On local ground or Bitbucket’s far domain,<br>
                To bar the joining of all errant code<br>
                That strays from vows once sworn at system dawn,<br>
                Our records writ when first the course was set.”</span>
                <br><span style="font-size:0.95em;color:#888;">— The Linter’s Lay (joke)</span>
            </blockquote>
        </footer>
    </div>
    
    {self._get_scripts()}
</body>
</html>"""

    def _render_summary(self, summary: LintSummary) -> str:
        """Render the summary dashboard."""
        status_class = "success" if summary.total_issues == 0 else (
            "error" if summary.errors > 0 else "warning"
        )
        status_text = "All Clear!" if summary.total_issues == 0 else (
            f"{summary.total_issues} Issue(s) Found"
        )
        
        return f"""
        <section class="summary {status_class}">
            <div class="summary-header">
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
            <div class="summary-stats">
                <div class="stat error">
                    <span class="stat-value">{summary.errors}</span>
                    <span class="stat-label">Errors</span>
                </div>
                <div class="stat warning">
                    <span class="stat-value">{summary.warnings}</span>
                    <span class="stat-label">Warnings</span>
                </div>
                <div class="stat info">
                    <span class="stat-value">{summary.infos}</span>
                    <span class="stat-label">Info</span>
                </div>
                <div class="stat neutral">
                    <span class="stat-value">{summary.files_scanned}</span>
                    <span class="stat-label">Files Scanned</span>
                </div>
                <div class="stat neutral">
                    <span class="stat-value">{summary.rules_executed}</span>
                    <span class="stat-label">Rules Executed</span>
                </div>
            </div>
        </section>"""

    def _render_files_section(self, by_file: Dict[Path, List[LintResult]]) -> str:
        """Render the files section."""
        if not by_file:
            return '<p class="no-issues">✓ No issues found in any files!</p>'
        
        sections = []
        for file_path in sorted(by_file.keys()):
            file_results = sorted(by_file[file_path], key=lambda r: r.line or 0)
            
            error_count = sum(1 for r in file_results if r.severity == Severity.ERROR)
            warning_count = sum(1 for r in file_results if r.severity == Severity.WARNING)
            info_count = sum(1 for r in file_results if r.severity == Severity.INFO)
            
            badges = []
            if error_count:
                badges.append(f'<span class="badge error">{error_count} E</span>')
            if warning_count:
                badges.append(f'<span class="badge warning">{warning_count} W</span>')
            if info_count:
                badges.append(f'<span class="badge info">{info_count} I</span>')
            
            # Create VS Code command URI for opening the file
            abs_path = file_path.resolve()
            # Use command:vscode.open instead of vscode://file/ for better compatibility
            encoded_path = str(abs_path).replace(' ', '%20')
            vscode_uri = f"command:vscode.open?%5B%22{encoded_path}%22%5D"
            
            issues_html = "\n".join(self._render_result(r, file_path) for r in file_results)
            file_view_html = self._render_file_view(file_path, file_results)
            
            sections.append(f"""
            <details class="file-section" open>
                <summary>
                    <a href="{vscode_uri}" class="file-path-link" title="Open in VS Code">{html.escape(str(file_path))}</a>
                    <span class="file-badges">{' '.join(badges)}</span>
                </summary>
                <div class="file-issues">
                    {issues_html}
                    {file_view_html}
                </div>
            </details>""")
        
        return "\n".join(sections)

    def _render_rules_section(self, by_rule: Dict[str, List[LintResult]], by_file: Dict[Path, List[LintResult]], rule_categories: Dict[str, str]) -> str:
        """Render the rules section with category grouping and file-based inline views."""
        if not by_rule:
            return '<p class="no-issues">✓ No issues found!</p>'
        
        # Group rules by category
        by_category: Dict[str, Dict[str, List[LintResult]]] = defaultdict(dict)
        for rule_id, rule_results in by_rule.items():
            category = rule_categories.get(rule_id, 'OTHER')
            by_category[category][rule_id] = rule_results
        
        category_sections = []
        for category in sorted(by_category.keys()):
            rules_in_category = by_category[category]
            
            # Calculate category totals
            cat_errors = sum(sum(1 for r in results if r.severity == Severity.ERROR) for results in rules_in_category.values())
            cat_warnings = sum(sum(1 for r in results if r.severity == Severity.WARNING) for results in rules_in_category.values())
            cat_infos = sum(sum(1 for r in results if r.severity == Severity.INFO) for results in rules_in_category.values())
            cat_total = cat_errors + cat_warnings + cat_infos
            
            cat_badges = []
            if cat_errors:
                cat_badges.append(f'<span class="badge error">{cat_errors} E</span>')
            if cat_warnings:
                cat_badges.append(f'<span class="badge warning">{cat_warnings} W</span>')
            if cat_infos:
                cat_badges.append(f'<span class="badge info">{cat_infos} I</span>')
            
            rule_sections = []
            for rule_id in sorted(rules_in_category.keys()):
                rule_results = rules_in_category[rule_id]
                rule_name = rule_results[0].rule_name or rule_id
                
                error_count = sum(1 for r in rule_results if r.severity == Severity.ERROR)
                warning_count = sum(1 for r in rule_results if r.severity == Severity.WARNING)
                info_count = sum(1 for r in rule_results if r.severity == Severity.INFO)
                
                badges = []
                if error_count:
                    badges.append(f'<span class="badge error">{error_count}</span>')
                if warning_count:
                    badges.append(f'<span class="badge warning">{warning_count}</span>')
                if info_count:
                    badges.append(f'<span class="badge info">{info_count}</span>')
                
                # Group results by file for this rule
                results_by_file: Dict[Path, List[LintResult]] = defaultdict(list)
                for r in rule_results:
                    results_by_file[r.file].append(r)
                
                # Render each file with its issues and inline file view
                file_sections = []
                for file_path in sorted(results_by_file.keys()):
                    file_results = sorted(results_by_file[file_path], key=lambda r: r.line or 0)
                    
                    abs_path = file_path.resolve()
                    encoded_path = str(abs_path).replace(' ', '%20')
                    vscode_uri = f"command:vscode.open?%5B%22{encoded_path}%22%5D"
                    
                    file_error_count = sum(1 for r in file_results if r.severity == Severity.ERROR)
                    file_warning_count = sum(1 for r in file_results if r.severity == Severity.WARNING)
                    file_info_count = sum(1 for r in file_results if r.severity == Severity.INFO)
                    
                    file_badges = []
                    if file_error_count:
                        file_badges.append(f'<span class="badge error">{file_error_count} E</span>')
                    if file_warning_count:
                        file_badges.append(f'<span class="badge warning">{file_warning_count} W</span>')
                    if file_info_count:
                        file_badges.append(f'<span class="badge info">{file_info_count} I</span>')
                    
                    # Render issues for this file
                    issues_html = "\n".join(self._render_result(r, file_path) for r in file_results)
                    
                    # Render inline file view for this file
                    file_view_html = self._render_file_view(file_path, file_results)
                    
                    file_sections.append(f"""
                    <details class="rule-file-section" open>
                        <summary>
                            <a href="{vscode_uri}" class="file-path-link" title="Open in VS Code">📄 {html.escape(str(file_path))}</a>
                            <span class="file-badges">{' '.join(file_badges)}</span>
                        </summary>
                        <div class="rule-file-issues">
                            {issues_html}
                            {file_view_html}
                        </div>
                    </details>""")
                
                files_html = "\n".join(file_sections)
                
                rule_sections.append(f"""
                <details class="rule-section" open>
                    <summary>
                        <span class="rule-id">{html.escape(rule_id)}</span>
                        <span class="rule-name">{html.escape(rule_name)}</span>
                        <span class="rule-count">{' '.join(badges)} ({len(rule_results)} occurrence(s))</span>
                    </summary>
                    <div class="rule-issues">
                        {files_html}
                    </div>
                </details>""")
            
            rules_html = "\n".join(rule_sections)
            
            category_sections.append(f"""
            <details class="category-section" open>
                <summary>
                    <span class="category-name">📁 {html.escape(category)}</span>
                    <span class="category-badges">{' '.join(cat_badges)}</span>
                    <span class="category-count">({cat_total} issue(s) in {len(rules_in_category)} rule(s))</span>
                </summary>
                <div class="category-rules">
                    {rules_html}
                </div>
            </details>""")
        
        return "\n".join(category_sections)

    def _render_result(self, result: LintResult, file_path: Optional[Path] = None) -> str:
        """Render a single result."""
        severity_class = result.severity.name.lower()
        
        # Create clickable line reference that scrolls to the line in file view AND opens in VS Code
        line_info = ""
        if result.line:
            line_anchor = f"line-{file_path.name}-{result.line}".replace(".", "-")
            abs_path = file_path.resolve()
            # Use command:vscode.open with line number for better compatibility
            encoded_path = str(abs_path).replace(' ', '%20')
            vscode_uri = f"command:vscode.open?%5B%22{encoded_path}%22%2C%7B%22selection%22%3A%7B%22start%22%3A%7B%22line%22%3A{result.line - 1}%2C%22character%22%3A0%7D%7D%7D%5D"
            line_info = f'<span class="line-info"><a href="#{line_anchor}" class="line-link" title="Jump to line in file view">Line {result.line}</a> <a href="{vscode_uri}" class="vscode-link" title="Open in VS Code">📝</a></span>'
        else:
            line_info = '<span class="line-info">File-level</span>'
        
        hint_html = ""
        if result.hint:
            hint_html = f"""
            <div class="issue-hint">
                <span class="hint-icon">💡</span>
                <span class="hint-text">{html.escape(result.hint)}</span>
            </div>"""
        
        context_html = ""
        if self.verbose and result.context:
            context_html = f"""
            <div class="issue-context">
                <code>{html.escape(result.context)}</code>
            </div>"""
        
        return f"""
        <div class="issue {severity_class}">
            <div class="issue-header">
                <span class="severity-badge {severity_class}">{result.severity.name}</span>
                <span class="rule-id">[{html.escape(result.rule_id)}]</span>
                {line_info}
            </div>
            <div class="issue-message">{html.escape(result.message)}</div>
            {context_html}
            {hint_html}
        </div>"""

    def _render_file_view(self, file_path: Path, results: List[LintResult]) -> str:
        """Render inline file viewer with syntax highlighting and issue markers."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except (OSError, IOError):
            return '<div class="file-view-error">Unable to read file</div>'
        
        if not lines:
            return ""
        
        # Map line numbers to results for highlighting
        issue_lines: Dict[int, List[LintResult]] = defaultdict(list)
        for result in results:
            if result.line:
                issue_lines[result.line].append(result)
        
        # Determine context range: show lines with issues plus surrounding context
        context_range = 3
        lines_to_show = set()
        for line_num in issue_lines.keys():
            for i in range(max(1, line_num - context_range), min(len(lines) + 1, line_num + context_range + 1)):
                lines_to_show.add(i)
        
        if not lines_to_show:
            return ""
        
        # Group consecutive lines for display
        sorted_lines = sorted(lines_to_show)
        line_groups = []
        current_group = [sorted_lines[0]]
        
        for line_num in sorted_lines[1:]:
            if line_num - current_group[-1] <= 1:
                current_group.append(line_num)
            else:
                line_groups.append(current_group)
                current_group = [line_num]
        line_groups.append(current_group)
        
        # Render file view
        file_view_html = '<div class="file-view">'
        file_view_html += '<details class="file-content" open><summary>📄 File View</summary>'
        
        for group in line_groups:
            for line_num in group:
                line_content = lines[line_num - 1].rstrip('\n')
                has_issue = line_num in issue_lines
                issue_class = "has-issue" if has_issue else ""
                line_anchor = f"line-{file_path.name}-{line_num}".replace(".", "-")
                
                file_view_html += f'''
        <div class="code-line {issue_class}" id="{line_anchor}">
            <span class="line-number">{line_num:4d}</span>
            <code class="line-content">{html.escape(line_content)}</code>'''
                
                # Show issue markers for this line
                if has_issue:
                    for issue in issue_lines[line_num]:
                        severity = issue.severity.name.lower()
                        file_view_html += f'''
            <div class="issue-marker {severity}">
                <strong>{issue.rule_id}</strong>: {html.escape(issue.message)}
            </div>'''
                
                file_view_html += '\n        </div>'
            
            # Add spacing between groups
            if group != line_groups[-1]:
                file_view_html += '\n        <div class="code-gap">...</div>\n'
        
        file_view_html += '\n    </details></div>'
        
        return file_view_html

    def _get_styles(self) -> str:
        """Get embedded CSS styles."""
        return """
    <style>
        :root {
            --color-error: #dc3545;
            --color-error-bg: #f8d7da;
            --color-warning: #ffc107;
            --color-warning-bg: #fff3cd;
            --color-info: #17a2b8;
            --color-info-bg: #d1ecf1;
            --color-success: #28a745;
            --color-success-bg: #d4edda;
            --color-neutral: #6c757d;
            --color-neutral-bg: #e9ecef;
        }
        
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            margin: 0;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        header h1 {
            margin: 0 0 10px 0;
            font-size: 2em;
        }
        
        .timestamp {
            opacity: 0.8;
            font-size: 0.9em;
            margin: 0;
        }
        
        .summary {
            padding: 20px 30px;
            border-bottom: 1px solid #eee;
        }
        
        .summary.success { background: var(--color-success-bg); }
        .summary.error { background: var(--color-error-bg); }
        .summary.warning { background: var(--color-warning-bg); }
        
        .summary-header {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            color: white;
        }
        
        .status-badge.success { background: var(--color-success); }
        .status-badge.error { background: var(--color-error); }
        .status-badge.warning { background: #e0a800; color: #333; }
        
        .summary-stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
        }
        
        .stat {
            text-align: center;
            padding: 15px 25px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .stat-value {
            display: block;
            font-size: 2em;
            font-weight: bold;
        }
        
        .stat.error .stat-value { color: var(--color-error); }
        .stat.warning .stat-value { color: #e0a800; }
        .stat.info .stat-value { color: var(--color-info); }
        .stat.neutral .stat-value { color: var(--color-neutral); }
        
        .stat-label {
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
        }
        
        .tabs {
            display: flex;
            background: #f8f9fa;
            border-bottom: 1px solid #ddd;
        }
        
        .tab-btn {
            flex: 1;
            padding: 15px 20px;
            border: none;
            background: none;
            cursor: pointer;
            font-size: 1em;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.2s;
        }
        
        .tab-btn:hover {
            background: #eee;
        }
        
        .tab-btn.active {
            color: #667eea;
            border-bottom-color: #667eea;
            background: white;
        }
        
        .tab-content {
            display: none;
            padding: 20px 30px;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .expand-controls {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
        }
        
        .expand-btn {
            padding: 8px 16px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.2s;
        }
        
        .expand-btn:hover {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        .category-section {
            margin-bottom: 20px;
            border: 2px solid #667eea;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .category-section > summary {
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 15px;
            font-weight: bold;
        }
        
        .category-section > summary:hover {
            opacity: 0.9;
        }
        
        .category-name {
            font-size: 1.1em;
        }
        
        .category-badges {
            display: flex;
            gap: 5px;
        }
        
        .category-count {
            margin-left: auto;
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .category-rules {
            padding: 15px;
            background: #f8f9fa;
        }
        
        .rule-file-section {
            margin: 10px 0;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            overflow: hidden;
            background: white;
        }
        
        .rule-file-section > summary {
            padding: 10px 15px;
            background: #f0f4f8;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .rule-file-section > summary:hover {
            background: #e8ecf0;
        }
        
        .rule-file-issues {
            padding: 10px;
            border-top: 1px solid #e0e0e0;
        }
        
        .no-issues {
            text-align: center;
            color: var(--color-success);
            font-size: 1.2em;
            padding: 40px;
        }
        
        .file-section, .rule-section {
            margin-bottom: 15px;
            border: 1px solid #ddd;
            border-radius: 6px;
            overflow: hidden;
        }
        
        .file-section summary, .rule-section summary {
            padding: 12px 15px;
            background: #f8f9fa;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .rule-section summary {
            background: linear-gradient(to right, #f8f9fa, #fff);
            border-bottom: 1px solid #e9ecef;
        }
        
        .file-section summary:hover, .rule-section summary:hover {
            background: #eee;
        }
        
        .file-path {
            font-family: monospace;
            flex-grow: 1;
            word-break: break-all;
        }
        
        .file-path-link {
            font-family: monospace;
            flex-grow: 1;
            word-break: break-all;
            color: inherit;
            text-decoration: none;
        }
        
        .file-path-link:hover {
            color: #667eea;
            text-decoration: underline;
        }
        
        .vscode-link {
            margin-left: 5px;
            text-decoration: none;
            font-size: 0.9em;
            opacity: 0.7;
            transition: opacity 0.2s;
        }
        
        .vscode-link:hover {
            opacity: 1;
        }
        
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
            font-weight: bold;
            color: white;
        }
        
        .badge.error { background: var(--color-error); }
        .badge.warning { background: #e0a800; color: #333; }
        .badge.info { background: var(--color-info); }
        
        .file-issues, .rule-issues {
            padding: 10px;
        }
        
        .issue {
            margin: 10px 0;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid;
        }
        
        .issue.error {
            background: var(--color-error-bg);
            border-color: var(--color-error);
        }
        
        .issue.warning {
            background: var(--color-warning-bg);
            border-color: var(--color-warning);
        }
        
        .issue.info {
            background: var(--color-info-bg);
            border-color: var(--color-info);
        }
        
        .issue-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }
        
        .severity-badge {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            font-weight: bold;
            text-transform: uppercase;
            color: white;
        }
        
        .severity-badge.error { background: var(--color-error); }
        .severity-badge.warning { background: #e0a800; color: #333; }
        .severity-badge.info { background: var(--color-info); }
        
        .rule-id {
            font-family: 'Courier New', Consolas, monospace;
            color: #2c3e50;
            font-size: 1em;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea15, #764ba215);
            padding: 4px 10px;
            border-radius: 4px;
            border-left: 3px solid #667eea;
            letter-spacing: 0.5px;
        }
        
        .line-info {
            color: #888;
            font-size: 0.85em;
        }
        
        .issue-message {
            font-weight: 500;
        }
        
        .issue-context {
            margin-top: 8px;
            padding: 8px;
            background: rgba(0,0,0,0.05);
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9em;
            overflow-x: auto;
        }
        
        .issue-hint {
            margin-top: 10px;
            padding: 8px 12px;
            background: var(--color-success-bg);
            border-radius: 4px;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }
        
        .hint-icon {
            font-size: 1.1em;
        }
        
        .hint-text {
            color: #155724;
        }
        
        .rule-issue {
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
        }
        
        .rule-issue:last-child {
            border-bottom: none;
        }
        
        .file-link {
            font-family: monospace;
            color: #667eea;
            margin-right: 10px;
            text-decoration: none;
        }
        
        .file-link:hover {
            text-decoration: underline;
        }
        
        .rule-name {
            flex-grow: 1;
            font-size: 1.05em;
            font-weight: 600;
            color: #34495e;
            margin-left: 8px;
        }
        
        .rule-count {
            color: #555;
            font-weight: 500;
            font-size: 0.9em;
            background: #e9ecef;
            padding: 3px 8px;
            border-radius: 12px;
        }
        
        /* File View Styles */
        .file-view {
            margin-top: 20px;
            border-top: 2px solid #ddd;
        }
        
        .file-content {
            margin: 0;
        }
        
        .file-content > summary {
            padding: 12px 15px;
            background: #f0f0f0;
            cursor: pointer;
            font-weight: bold;
            user-select: none;
        }
        
        .file-content > summary:hover {
            background: #e8e8e8;
        }
        
        .code-line {
            display: flex;
            align-items: flex-start;
            padding: 4px 0;
            border-left: 3px solid transparent;
            background: white;
        }
        
        .code-line.has-issue {
            background: rgba(220, 53, 69, 0.05);
            border-left-color: #dc3545;
            padding-left: 12px;
        }
        
        .line-number {
            display: inline-block;
            width: 50px;
            padding: 0 10px;
            text-align: right;
            color: #999;
            font-family: monospace;
            font-size: 0.85em;
            user-select: none;
            flex-shrink: 0;
        }
        
        .line-content {
            flex-grow: 1;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #333;
            white-space: pre-wrap;
            word-wrap: break-word;
            margin: 0;
            padding: 0 10px;
        }
        
        .code-gap {
            text-align: center;
            color: #999;
            padding: 8px;
            font-size: 0.9em;
            font-style: italic;
        }
        
        .issue-marker {
            display: block;
            width: 100%;
            margin-left: 50px;
            padding: 8px 10px;
            margin-top: 4px;
            border-radius: 4px;
            font-size: 0.85em;
            background: rgba(0, 0, 0, 0.02);
        }
        
        .issue-marker.error {
            background: var(--color-error-bg);
            border-left: 3px solid var(--color-error);
            color: var(--color-error);
        }
        
        .issue-marker.warning {
            background: var(--color-warning-bg);
            border-left: 3px solid var(--color-warning);
            color: #856404;
        }
        
        .issue-marker.info {
            background: var(--color-info-bg);
            border-left: 3px solid var(--color-info);
            color: var(--color-info);
        }
        
        .issue-marker strong {
            color: inherit;
            margin-right: 8px;
        }
        
        .line-link {
            color: inherit;
            text-decoration: none;
            border-bottom: 1px dotted #667eea;
        }
        
        .line-link:hover {
            color: #667eea;
        }
        
        .rule-file-link {
            color: #667eea;
            text-decoration: none;
            font-size: 0.85em;
            margin-left: 5px;
        }
        
        .rule-file-link:hover {
            text-decoration: underline;
        }
        
        footer {
            padding: 20px;
            text-align: center;
            background: #f8f9fa;
            color: #666;
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            
            .summary-stats {
                gap: 15px;
            }
            
            .stat {
                padding: 10px 15px;
            }
            
            .stat-value {
                font-size: 1.5em;
            }
        }
    </style>"""

    def _get_scripts(self) -> str:
        """Get embedded JavaScript."""
        return """
    <script>
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // Deactivate all tabs
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                // Activate clicked tab
                btn.classList.add('active');
                document.getElementById(btn.dataset.tab).classList.add('active');
            });
        });
        
        // Expand/Collapse all functionality with two levels for rules tab
        document.querySelectorAll('.expand-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                const target = btn.dataset.target;
                const container = document.getElementById(target);
                
                if (container) {
                    if (action === 'expand-all') {
                        // Expand everything
                        container.querySelectorAll('details').forEach(d => d.setAttribute('open', ''));
                    } else if (action === 'collapse-all') {
                        // Collapse everything
                        container.querySelectorAll('details').forEach(d => d.removeAttribute('open'));
                    } else if (action === 'expand-level1') {
                        // Expand only categories and rules, NOT file content
                        container.querySelectorAll('details.category-section').forEach(d => d.setAttribute('open', ''));
                        container.querySelectorAll('details.rule-section').forEach(d => d.setAttribute('open', ''));
                        // Keep file sections collapsed
                        container.querySelectorAll('details.rule-file-section').forEach(d => d.removeAttribute('open'));
                        container.querySelectorAll('details.file-content').forEach(d => d.removeAttribute('open'));
                    } else if (action === 'collapse-level1') {
                        // Collapse rules but keep categories open
                        container.querySelectorAll('details.category-section').forEach(d => d.setAttribute('open', ''));
                        container.querySelectorAll('details.rule-section').forEach(d => d.removeAttribute('open'));
                        container.querySelectorAll('details.rule-file-section').forEach(d => d.removeAttribute('open'));
                        container.querySelectorAll('details.file-content').forEach(d => d.removeAttribute('open'));
                    }
                }
            });
        });
        
        // Smooth scroll to anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const targetId = this.getAttribute('href').slice(1);
                const target = document.getElementById(targetId);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    // Highlight the target briefly
                    target.style.transition = 'background-color 0.3s';
                    target.style.backgroundColor = '#fff3cd';
                    setTimeout(() => {
                        target.style.backgroundColor = '';
                    }, 2000);
                }
            });
        });
    </script>"""
