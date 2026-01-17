"""
HTML output formatter for visual reports.

Generates a standalone HTML report with:
- Summary dashboard
- Per-file issue breakdown
- Color-coded severities
- Expandable sections
- How-to-fix hints

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
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
<!--
    Bake Linter Report
    (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
    All rights reserved.
-->
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(self.title)}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    {self._get_styles()}
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 {html.escape(self.title)}</h1>
            <p class="timestamp">Generated: {timestamp}</p>
            <div class="copyright-section">
                <p class="copyright-main">© 2024-2026 <a href="https://www.apliant.com.br/cv" target="_blank" class="author-link">Eduardo Correia</a> — <a href="https://www.apliant.com.br/cv" target="_blank" class="cv-link">📄 Curriculum Vitae</a></p>
                <p class="copyright-links">
                    <a href="mailto:ecorreia@apliant.com.br" class="contact-link">📧 ecorreia@apliant.com.br</a>
                    <span class="link-separator">•</span>
                    <a href="https://www.apliant.com.br" target="_blank" class="contact-link">🌐 www.apliant.com.br</a>
                    <span class="link-separator">•</span>
                    <a href="https://www.linkedin.com/in/c99-eduardo/" target="_blank" class="contact-link linkedin-link">💼 LinkedIn</a>
                </p>
            </div>
        </header>
        
        {self._render_summary(summary)}
        
        <nav class="tabs">
            <button class="tab-btn" data-tab="files">📁 By File</button>
            <button class="tab-btn active" data-tab="rules">📋 By Rule</button>
            <button class="tab-btn" data-tab="statistics">📊 Statistics</button>
        </nav>
        
        <div class="severity-filters">
            <span class="filter-label">Filter by Severity:</span>
            <button class="filter-btn active" data-severity="error">🔴 Errors</button>
            <button class="filter-btn active" data-severity="warning">🟡 Warnings</button>
            <button class="filter-btn active" data-severity="info">🔵 Info</button>
        </div>
        
        <div id="files" class="tab-content">
            <div class="expand-controls">
                <button class="expand-btn" data-action="expand-all" data-target="files">▼ Expand All</button>
                <button class="expand-btn" data-action="collapse-all" data-target="files">▲ Collapse All</button>
            </div>
            {self._render_files_section(by_file)}
        </div>
        
        <div id="rules" class="tab-content active">
            <div class="expand-controls">
                <button class="expand-btn" data-action="expand-all" data-target="rules">▼▼ Items</button>
                <button class="expand-btn" data-action="expand-level1" data-target="rules">▲ Files</button>
                <button class="expand-btn" data-action="collapse-level1" data-target="rules">▲▲ Rules</button>
                <button class="expand-btn" data-action="collapse-all" data-target="rules">▲▲▲ Categories</button>
            </div>
            {self._render_rules_section(by_rule, by_file, rule_categories)}
        </div>
        
        <div id="statistics" class="tab-content">
            {self._render_statistics_section(summary, by_rule, by_file, rule_categories)}
        </div>
        
        <footer>
            <p>Bake Linter Report • {summary.total_issues} issue(s) in {summary.files_scanned} file(s)</p>
            <blockquote style="margin:2em 0 0 0;padding:1em 1.5em;background:#f8f9fa;border-left:5px solid #667eea;font-style:italic;color:#444;">
                <span style="font-size:1.1em;">“A linter this, that runs by hearth or hall,<br>
                On local ground or Bitbucket’s far domain,<br>
                To bar the joining of all errant code<br>
                That strays from vows once sworn at system dawn,<br>
                Our records writ when first the course was set.”</span>
                <br><span style="font-size:0.95em;color:#888;">— The Linter’s Lay</span>
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
                <details class="rule-section" open data-total-occurrences="{len(rule_results)}">
                    <summary>
                        <span class="rule-id">{html.escape(rule_id)}</span>
                        <span class="rule-name">{html.escape(rule_name)}</span>
                        <span class="rule-count">{' '.join(badges)} (<span class="occurrence-count">{len(rule_results)}</span> occurrence(s))</span>
                    </summary>
                    <div class="rule-issues">
                        {files_html}
                    </div>
                </details>""")
            
            rules_html = "\n".join(rule_sections)
            
            category_sections.append(f"""
            <details class="category-section" open data-total-issues="{cat_total}" data-total-rules="{len(rules_in_category)}">
                <summary>
                    <span class="category-name">📁 {html.escape(category)}</span>
                    <span class="category-badges">{' '.join(cat_badges)}</span>
                    <span class="category-count">(<span class="issue-count">{cat_total}</span> issue(s) in <span class="rule-count-num">{len(rules_in_category)}</span> rule(s))</span>
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
        <div class="issue {severity_class}" data-rule-id="{html.escape(result.rule_id)}" data-rule-name="{html.escape(result.rule_name)}">
            <div class="issue-header">
                <span class="severity-badge {severity_class}">{result.severity.name}</span>
                <span class="rule-id">[{html.escape(result.rule_id)}]</span>
                <span class="rule-name" style="display:none;">{html.escape(result.rule_name)}</span>
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

    def _render_statistics_section(
        self,
        summary: LintSummary,
        by_rule: Dict[str, List[LintResult]],
        by_file: Dict[Path, List[LintResult]],
        rule_categories: Dict[str, str],
    ) -> str:
        """Render the statistics section with charts."""
        import json
        
        # Prepare data for charts
        severity_data = {
            'labels': ['Errors', 'Warnings', 'Info'],
            'values': [summary.errors, summary.warnings, summary.infos],
            'colors': ['#dc3545', '#ffc107', '#17a2b8'],
        }
        
        # Category data
        category_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {'errors': 0, 'warnings': 0, 'infos': 0})
        for rule_id, rule_results in by_rule.items():
            category = rule_categories.get(rule_id, 'OTHER')
            for r in rule_results:
                if r.severity == Severity.ERROR:
                    category_counts[category]['errors'] += 1
                elif r.severity == Severity.WARNING:
                    category_counts[category]['warnings'] += 1
                else:
                    category_counts[category]['infos'] += 1
        
        # Top rules by issue count with severity breakdown for stacked charts
        rule_stats = []
        for rule_id, results in by_rule.items():
            errors = sum(1 for r in results if r.severity == Severity.ERROR)
            warnings = sum(1 for r in results if r.severity == Severity.WARNING)
            infos = sum(1 for r in results if r.severity == Severity.INFO)
            total = errors + warnings + infos
            rule_name = results[0].rule_name if results else rule_id
            rule_stats.append((rule_id, total, rule_name, errors, warnings, infos))
        top_rules = sorted(rule_stats, key=lambda x: -x[1])[:15]
        
        # File issues distribution with severity breakdown for stacked charts
        file_stats = []
        for f, results in by_file.items():
            errors = sum(1 for r in results if r.severity == Severity.ERROR)
            warnings = sum(1 for r in results if r.severity == Severity.WARNING)
            infos = sum(1 for r in results if r.severity == Severity.INFO)
            total = errors + warnings + infos
            file_stats.append((str(f.name), total, errors, warnings, infos))
        top_files = sorted(file_stats, key=lambda x: -x[1])[:10]
        
        # Encode data for JavaScript
        severity_json = json.dumps(severity_data)
        category_labels = json.dumps(list(category_counts.keys()))
        category_errors = json.dumps([v['errors'] for v in category_counts.values()])
        category_warnings = json.dumps([v['warnings'] for v in category_counts.values()])
        category_infos = json.dumps([v['infos'] for v in category_counts.values()])
        
        top_rule_labels = json.dumps([r[0] for r in top_rules])
        top_rule_values = json.dumps([r[1] for r in top_rules])
        top_rule_names = json.dumps([r[2] for r in top_rules])  # Rule names for tooltips
        top_rule_errors = json.dumps([r[3] for r in top_rules])
        top_rule_warnings = json.dumps([r[4] for r in top_rules])
        top_rule_infos = json.dumps([r[5] for r in top_rules])
        
        top_file_labels = json.dumps([f[0] for f in top_files])
        top_file_values = json.dumps([f[1] for f in top_files])
        top_file_errors = json.dumps([f[2] for f in top_files])
        top_file_warnings = json.dumps([f[3] for f in top_files])
        top_file_infos = json.dumps([f[4] for f in top_files])
        
        return f"""
        <div class="statistics-container">
            <h2>📊 Analysis Dashboard</h2>
            
            <div class="stats-grid">
                <div class="chart-card">
                    <h3>🎯 Severity Distribution</h3>
                    <div class="chart-wrapper">
                        <canvas id="severityPieChart"></canvas>
                    </div>
                    <p class="chart-description">Distribution of issues by severity level</p>
                </div>
                
                <div class="chart-card">
                    <h3>📊 Severity Breakdown</h3>
                    <div class="chart-wrapper">
                        <canvas id="severityDoughnutChart"></canvas>
                    </div>
                    <p class="chart-description">Proportional view of issue types</p>
                </div>
                
                <div class="chart-card wide">
                    <h3>📁 Issues by Category</h3>
                    <div class="chart-wrapper-wide">
                        <canvas id="categoryBarChart"></canvas>
                    </div>
                    <p class="chart-description">Stacked bar chart showing errors, warnings, and info by rule category</p>
                </div>
                
                <div class="chart-card wide">
                    <h3>🔝 Top 15 Rules by Issue Count</h3>
                    <div class="chart-wrapper-wide">
                        <canvas id="topRulesChart"></canvas>
                    </div>
                    <p class="chart-description">Rules that generated the most issues</p>
                </div>
                
                <div class="chart-card wide">
                    <h3>📄 Top 10 Files by Issue Count</h3>
                    <div class="chart-wrapper-wide">
                        <canvas id="topFilesChart"></canvas>
                    </div>
                    <p class="chart-description">Files with the highest number of issues</p>
                </div>
                
                <div class="chart-card">
                    <h3>📈 Quick Stats</h3>
                    <div class="quick-stats">
                        <div class="quick-stat">
                            <span class="qs-value" id="qs-total-issues">{summary.total_issues}</span>
                            <span class="qs-label">Total Issues</span>
                        </div>
                        <div class="quick-stat">
                            <span class="qs-value" id="qs-files-with-issues">{len(by_file)}</span>
                            <span class="qs-label">Files with Issues</span>
                        </div>
                        <div class="quick-stat">
                            <span class="qs-value" id="qs-rules-triggered">{len(by_rule)}</span>
                            <span class="qs-label">Rules Triggered</span>
                        </div>
                        <div class="quick-stat">
                            <span class="qs-value" id="qs-categories-affected">{len(category_counts)}</span>
                            <span class="qs-label">Categories Affected</span>
                        </div>
                        <div class="quick-stat">
                            <span class="qs-value" id="qs-avg-issues-file">{summary.total_issues / max(len(by_file), 1):.1f}</span>
                            <span class="qs-label">Avg Issues/File</span>
                        </div>
                        <div class="quick-stat error-highlight">
                            <span class="qs-value" id="qs-error-rate">{(summary.errors / max(summary.total_issues, 1) * 100):.1f}%</span>
                            <span class="qs-label">Error Rate</span>
                        </div>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3>🏆 Health Score</h3>
                    <div class="health-score-container">
                        <canvas id="healthGauge"></canvas>
                        <div class="health-score-text">
                            <span class="health-value" id="healthValue">--</span>
                            <span class="health-label">Code Health</span>
                        </div>
                    </div>
                    <p class="chart-description">Based on error/warning ratio and issue density</p>
                </div>
            </div>
        </div>
        
        <script id="chart-data" type="application/json">
        {{
            "severity": {severity_json},
            "categoryLabels": {category_labels},
            "categoryErrors": {category_errors},
            "categoryWarnings": {category_warnings},
            "categoryInfos": {category_infos},
            "topRuleLabels": {top_rule_labels},
            "topRuleValues": {top_rule_values},
            "topRuleNames": {top_rule_names},
            "topRuleErrors": {top_rule_errors},
            "topRuleWarnings": {top_rule_warnings},
            "topRuleInfos": {top_rule_infos},
            "topFileLabels": {top_file_labels},
            "topFileValues": {top_file_values},
            "topFileErrors": {top_file_errors},
            "topFileWarnings": {top_file_warnings},
            "topFileInfos": {top_file_infos},
            "totalIssues": {summary.total_issues},
            "errors": {summary.errors},
            "warnings": {summary.warnings},
            "infos": {summary.infos},
            "filesScanned": {summary.files_scanned}
        }}
        </script>
        """

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
        
        .copyright-section {
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.2);
        }
        
        .copyright-main {
            opacity: 0.95;
            font-size: 0.95em;
            margin: 0 0 8px 0;
        }
        
        .copyright-main a {
            color: white;
            text-decoration: none;
            font-weight: 500;
        }
        
        .copyright-main a:hover {
            text-decoration: underline;
        }
        
        .author-link {
            font-weight: 600 !important;
        }
        
        .cv-link {
            opacity: 0.9;
            margin-left: 5px;
        }
        
        .copyright-links {
            opacity: 0.9;
            font-size: 0.85em;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .contact-link {
            color: white;
            text-decoration: none;
            padding: 3px 8px;
            border-radius: 4px;
            transition: background-color 0.2s, transform 0.2s;
        }
        
        .contact-link:hover {
            background-color: rgba(255,255,255,0.15);
            transform: translateY(-1px);
        }
        
        .linkedin-link:hover {
            background-color: rgba(10, 102, 194, 0.4);
        }
        
        .link-separator {
            opacity: 0.5;
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
        
        .severity-filters {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 30px;
            background: #f0f4f8;
            border-bottom: 1px solid #ddd;
        }
        
        .filter-label {
            font-weight: 600;
            color: #555;
            margin-right: 10px;
        }
        
        .filter-btn {
            padding: 8px 16px;
            border: 2px solid #ddd;
            background: #f8f9fa;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
            transition: all 0.2s;
            opacity: 0.5;
        }
        
        .filter-btn:hover {
            background: #e9ecef;
        }
        
        .filter-btn.active {
            opacity: 1;
            border-color: currentColor;
        }
        
        .filter-btn[data-severity="error"] {
            color: var(--color-error);
        }
        
        .filter-btn[data-severity="error"].active {
            background: var(--color-error-bg);
            border-color: var(--color-error);
        }
        
        .filter-btn[data-severity="warning"] {
            color: #856404;
        }
        
        .filter-btn[data-severity="warning"].active {
            background: var(--color-warning-bg);
            border-color: var(--color-warning);
        }
        
        .filter-btn[data-severity="info"] {
            color: var(--color-info);
        }
        
        .filter-btn[data-severity="info"].active {
            background: var(--color-info-bg);
            border-color: var(--color-info);
        }
        
        .issue.hidden-by-filter,
        .file-section.hidden-by-filter,
        .rule-section.hidden-by-filter,
        .category-section.hidden-by-filter,
        .rule-file-section.hidden-by-filter {
            display: none !important;
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
        
        /* Statistics Section Styles */
        .statistics-container {
            padding: 20px;
        }
        
        .statistics-container h2 {
            color: #667eea;
            margin-bottom: 25px;
            text-align: center;
            font-size: 1.8em;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }
        
        .chart-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .chart-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .chart-card.wide {
            grid-column: span 2;
        }
        
        .chart-card h3 {
            margin: 0 0 15px 0;
            color: #333;
            font-size: 1.1em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .chart-wrapper {
            position: relative;
            height: 250px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .chart-wrapper-wide {
            position: relative;
            height: 300px;
        }
        
        .chart-description {
            text-align: center;
            color: #888;
            font-size: 0.85em;
            margin-top: 10px;
            font-style: italic;
        }
        
        .quick-stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .quick-stat {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            transition: transform 0.2s;
        }
        
        .quick-stat:hover {
            transform: scale(1.02);
        }
        
        .quick-stat.error-highlight {
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        }
        
        .qs-value {
            display: block;
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
        }
        
        .error-highlight .qs-value {
            color: #dc3545;
        }
        
        .qs-label {
            display: block;
            font-size: 0.8em;
            color: #666;
            text-transform: uppercase;
            margin-top: 5px;
        }
        
        .health-score-container {
            position: relative;
            height: 200px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        .health-score-text {
            position: absolute;
            text-align: center;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }
        
        .health-value {
            display: block;
            font-size: 2.5em;
            font-weight: bold;
            color: #28a745;
        }
        
        .health-label {
            display: block;
            font-size: 0.9em;
            color: #666;
        }
        
        @media (max-width: 1024px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .chart-card.wide {
                grid-column: span 1;
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
        
        // Severity filter functionality
        function applySeverityFilters() {
            const activeFilters = Array.from(document.querySelectorAll('.filter-btn.active'))
                .map(btn => btn.dataset.severity);
            
            // Filter individual issues
            document.querySelectorAll('.issue').forEach(issue => {
                const severity = issue.classList.contains('error') ? 'error' :
                                issue.classList.contains('warning') ? 'warning' : 'info';
                if (activeFilters.includes(severity)) {
                    issue.classList.remove('hidden-by-filter');
                } else {
                    issue.classList.add('hidden-by-filter');
                }
            });
            
            // Filter issue markers in file view
            document.querySelectorAll('.issue-marker').forEach(marker => {
                const severity = marker.classList.contains('error') ? 'error' :
                                marker.classList.contains('warning') ? 'warning' : 'info';
                if (activeFilters.includes(severity)) {
                    marker.classList.remove('hidden-by-filter');
                } else {
                    marker.classList.add('hidden-by-filter');
                }
            });
            
            // Hide file sections with no visible issues (By File tab)
            document.querySelectorAll('#files .file-section').forEach(section => {
                const visibleIssues = section.querySelectorAll('.issue:not(.hidden-by-filter)');
                if (visibleIssues.length === 0) {
                    section.classList.add('hidden-by-filter');
                } else {
                    section.classList.remove('hidden-by-filter');
                }
            });
            
            // Hide rule-file sections with no visible issues (By Rules tab)
            document.querySelectorAll('.rule-file-section').forEach(section => {
                const visibleIssues = section.querySelectorAll('.issue:not(.hidden-by-filter)');
                if (visibleIssues.length === 0) {
                    section.classList.add('hidden-by-filter');
                } else {
                    section.classList.remove('hidden-by-filter');
                }
            });
            
            // Hide rule sections with no visible file sections and update occurrence counts
            document.querySelectorAll('.rule-section').forEach(section => {
                const visibleFileSections = section.querySelectorAll('.rule-file-section:not(.hidden-by-filter)');
                const visibleIssues = section.querySelectorAll('.issue:not(.hidden-by-filter)');
                if (visibleFileSections.length === 0) {
                    section.classList.add('hidden-by-filter');
                } else {
                    section.classList.remove('hidden-by-filter');
                }
                // Update occurrence count
                const countSpan = section.querySelector('.occurrence-count');
                if (countSpan) {
                    countSpan.textContent = visibleIssues.length;
                }
            });
            
            // Hide category sections with no visible rule sections and update counts
            document.querySelectorAll('.category-section').forEach(section => {
                const visibleRuleSections = section.querySelectorAll('.rule-section:not(.hidden-by-filter)');
                const visibleIssues = section.querySelectorAll('.issue:not(.hidden-by-filter)');
                if (visibleRuleSections.length === 0) {
                    section.classList.add('hidden-by-filter');
                } else {
                    section.classList.remove('hidden-by-filter');
                }
                // Update issue count
                const issueCountSpan = section.querySelector('.issue-count');
                if (issueCountSpan) {
                    issueCountSpan.textContent = visibleIssues.length;
                }
                // Update rule count
                const ruleCountSpan = section.querySelector('.rule-count-num');
                if (ruleCountSpan) {
                    ruleCountSpan.textContent = visibleRuleSections.length;
                }
            });
            
            // Update summary stats - ONLY count from #files to avoid double-counting
            const visibleErrors = document.querySelectorAll('#files .issue.error:not(.hidden-by-filter)').length;
            const visibleWarnings = document.querySelectorAll('#files .issue.warning:not(.hidden-by-filter)').length;
            const visibleInfos = document.querySelectorAll('#files .issue.info:not(.hidden-by-filter)').length;
            
            // Update summary stat values if they exist
            const errorStat = document.querySelector('.stat.error .stat-value');
            const warningStat = document.querySelector('.stat.warning .stat-value');
            const infoStat = document.querySelector('.stat.info .stat-value');
            
            if (errorStat) errorStat.textContent = visibleErrors;
            if (warningStat) warningStat.textContent = visibleWarnings;
            if (infoStat) infoStat.textContent = visibleInfos;
            
            // Update charts if they exist
            updateChartsWithFilter(visibleErrors, visibleWarnings, visibleInfos);
        }
        
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.classList.toggle('active');
                applySeverityFilters();
            });
        });
        
        // Apply filters on page load (all active by default)
        applySeverityFilters();
        
        // Initialize Charts when Statistics tab is shown
        let chartsInitialized = false;
        
        function initializeCharts() {
            if (chartsInitialized) return;
            
            const dataElement = document.getElementById('chart-data');
            if (!dataElement) return;
            
            const data = JSON.parse(dataElement.textContent);
            chartsInitialized = true;
            
            // Color palette
            const colors = {
                error: '#dc3545',
                warning: '#ffc107',
                info: '#17a2b8',
                primary: '#667eea',
                secondary: '#764ba2',
                success: '#28a745',
                gradient: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe']
            };
            
            // Store chart references for dynamic updates
            window.linterCharts = window.linterCharts || {};
            
            // Severity Pie Chart
            const severityPieCtx = document.getElementById('severityPieChart');
            if (severityPieCtx) {
                window.linterCharts.severityPie = new Chart(severityPieCtx, {
                    type: 'pie',
                    data: {
                        labels: data.severity.labels,
                        datasets: [{
                            data: data.severity.values,
                            backgroundColor: data.severity.colors,
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: { padding: 15, usePointStyle: true }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const percentage = total > 0 ? ((context.raw / total) * 100).toFixed(1) : 0;
                                        return `${context.label}: ${context.raw} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
            
            // Severity Doughnut Chart
            const doughnutCtx = document.getElementById('severityDoughnutChart');
            if (doughnutCtx) {
                window.linterCharts.severityDoughnut = new Chart(doughnutCtx, {
                    type: 'doughnut',
                    data: {
                        labels: data.severity.labels,
                        datasets: [{
                            data: data.severity.values,
                            backgroundColor: data.severity.colors,
                            borderWidth: 3,
                            borderColor: '#fff',
                            hoverOffset: 10
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '60%',
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: { padding: 15, usePointStyle: true }
                            }
                        }
                    }
                });
            }
            
            // Category Stacked Bar Chart
            const categoryCtx = document.getElementById('categoryBarChart');
            if (categoryCtx && data.categoryLabels.length > 0) {
                window.linterCharts.categoryBar = new Chart(categoryCtx, {
                    type: 'bar',
                    data: {
                        labels: data.categoryLabels,
                        datasets: [
                            {
                                label: 'Errors',
                                data: data.categoryErrors,
                                backgroundColor: colors.error,
                                borderRadius: 4
                            },
                            {
                                label: 'Warnings',
                                data: data.categoryWarnings,
                                backgroundColor: colors.warning,
                                borderRadius: 4
                            },
                            {
                                label: 'Info',
                                data: data.categoryInfos,
                                backgroundColor: colors.info,
                                borderRadius: 4
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                stacked: true,
                                grid: { display: false }
                            },
                            y: {
                                stacked: true,
                                beginAtZero: true
                            }
                        },
                        plugins: {
                            legend: {
                                position: 'top'
                            }
                        }
                    }
                });
            }
            
            // Top Rules Horizontal Stacked Bar Chart with severity breakdown
            const topRulesCtx = document.getElementById('topRulesChart');
            if (topRulesCtx && data.topRuleLabels.length > 0) {
                window.linterCharts.topRules = new Chart(topRulesCtx, {
                    type: 'bar',
                    data: {
                        labels: data.topRuleLabels,
                        datasets: [
                            {
                                label: 'Errors',
                                data: data.topRuleErrors || [],
                                backgroundColor: colors.error,
                                borderRadius: 0
                            },
                            {
                                label: 'Warnings',
                                data: data.topRuleWarnings || [],
                                backgroundColor: colors.warning,
                                borderRadius: 0
                            },
                            {
                                label: 'Info',
                                data: data.topRuleInfos || [],
                                backgroundColor: colors.info,
                                borderRadius: 0
                            }
                        ]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                stacked: true,
                                beginAtZero: true,
                                grid: { color: '#f0f0f0' }
                            },
                            y: {
                                stacked: true,
                                grid: { display: false },
                                ticks: { font: { family: 'monospace', size: 10 } }
                            }
                        },
                        plugins: {
                            legend: { position: 'top' },
                            tooltip: {
                                callbacks: {
                                    title: function(context) {
                                        const idx = context[0].dataIndex;
                                        const ruleId = data.topRuleLabels[idx];
                                        const ruleName = data.topRuleNames ? data.topRuleNames[idx] : '';
                                        return ruleName ? `${ruleId}: ${ruleName}` : ruleId;
                                    },
                                    afterTitle: function(context) {
                                        const idx = context[0].dataIndex;
                                        const errors = data.topRuleErrors ? data.topRuleErrors[idx] : 0;
                                        const warnings = data.topRuleWarnings ? data.topRuleWarnings[idx] : 0;
                                        const infos = data.topRuleInfos ? data.topRuleInfos[idx] : 0;
                                        const total = errors + warnings + infos;
                                        return `Total: ${total} issues`;
                                    },
                                    label: function(context) {
                                        return `${context.dataset.label}: ${context.raw}`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
            
            // Top Files Stacked Bar Chart with severity breakdown
            const topFilesCtx = document.getElementById('topFilesChart');
            if (topFilesCtx && data.topFileLabels.length > 0) {
                window.linterCharts.topFiles = new Chart(topFilesCtx, {
                    type: 'bar',
                    data: {
                        labels: data.topFileLabels,
                        datasets: [
                            {
                                label: 'Errors',
                                data: data.topFileErrors || [],
                                backgroundColor: colors.error,
                                borderRadius: 0
                            },
                            {
                                label: 'Warnings',
                                data: data.topFileWarnings || [],
                                backgroundColor: colors.warning,
                                borderRadius: 0
                            },
                            {
                                label: 'Info',
                                data: data.topFileInfos || [],
                                backgroundColor: colors.info,
                                borderRadius: 0
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                stacked: true,
                                beginAtZero: true
                            },
                            x: {
                                stacked: true,
                                ticks: {
                                    maxRotation: 45,
                                    minRotation: 45,
                                    font: { size: 9 }
                                }
                            }
                        },
                        plugins: {
                            legend: { position: 'top' },
                            tooltip: {
                                callbacks: {
                                    title: function(context) {
                                        return context[0].label;
                                    },
                                    afterTitle: function(context) {
                                        const idx = context[0].dataIndex;
                                        const errors = data.topFileErrors ? data.topFileErrors[idx] : 0;
                                        const warnings = data.topFileWarnings ? data.topFileWarnings[idx] : 0;
                                        const infos = data.topFileInfos ? data.topFileInfos[idx] : 0;
                                        const total = errors + warnings + infos;
                                        return `Total: ${total} issues`;
                                    },
                                    label: function(context) {
                                        return `${context.dataset.label}: ${context.raw}`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
            
            // Health Gauge Chart
            const healthCtx = document.getElementById('healthGauge');
            if (healthCtx) {
                // Calculate health score (0-100)
                // Lower is better: more errors = lower score
                const errorWeight = 10;
                const warningWeight = 3;
                const infoWeight = 1;
                
                const infos = data.infos || (data.totalIssues - data.errors - data.warnings);
                const weightedScore = (data.errors * errorWeight) + 
                                      (data.warnings * warningWeight) + 
                                      (infos * infoWeight);
                
                // Normalize to 0-100 (lower weighted score = higher health)
                const maxExpectedScore = data.filesScanned * 50; // Assume max 50 weighted issues per file
                let healthScore = Math.max(0, 100 - (weightedScore / Math.max(maxExpectedScore, 1)) * 100);
                healthScore = Math.min(100, Math.round(healthScore));
                
                // Update the text
                const healthValueEl = document.getElementById('healthValue');
                if (healthValueEl) {
                    healthValueEl.textContent = healthScore;
                    if (healthScore >= 80) {
                        healthValueEl.style.color = '#28a745';
                    } else if (healthScore >= 50) {
                        healthValueEl.style.color = '#ffc107';
                    } else {
                        healthValueEl.style.color = '#dc3545';
                    }
                }
                
                window.linterCharts.healthGauge = new Chart(healthCtx, {
                    type: 'doughnut',
                    data: {
                        datasets: [{
                            data: [healthScore, 100 - healthScore],
                            backgroundColor: [
                                healthScore >= 80 ? '#28a745' : healthScore >= 50 ? '#ffc107' : '#dc3545',
                                '#e9ecef'
                            ],
                            borderWidth: 0,
                            circumference: 180,
                            rotation: 270
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '75%',
                        plugins: {
                            legend: { display: false },
                            tooltip: { enabled: false }
                        }
                    }
                });
            }
        }
        
        // Function to update charts when filters change
        function updateChartsWithFilter(errors, warnings, infos) {
            const charts = window.linterCharts;
            if (!charts) return;
            
            const dataElement = document.getElementById('chart-data');
            const originalData = dataElement ? JSON.parse(dataElement.textContent) : null;
            
            // Get active filters
            const showError = document.querySelector('.filter-btn[data-severity="error"]').classList.contains('active');
            const showWarning = document.querySelector('.filter-btn[data-severity="warning"]').classList.contains('active');
            const showInfo = document.querySelector('.filter-btn[data-severity="info"]').classList.contains('active');
            
            // Update pie chart
            if (charts.severityPie) {
                charts.severityPie.data.datasets[0].data = [errors, warnings, infos];
                charts.severityPie.update('none');
            }
            
            // Update doughnut chart
            if (charts.severityDoughnut) {
                charts.severityDoughnut.data.datasets[0].data = [errors, warnings, infos];
                charts.severityDoughnut.update('none');
            }
            
            // Update health gauge
            if (charts.healthGauge) {
                const errorWeight = 10;
                const warningWeight = 3;
                const infoWeight = 1;
                const totalIssues = errors + warnings + infos;
                
                const weightedScore = (errors * errorWeight) + 
                                      (warnings * warningWeight) + 
                                      (infos * infoWeight);
                
                const maxExpectedScore = (originalData ? originalData.filesScanned : 1) * 50;
                let healthScore = Math.max(0, 100 - (weightedScore / Math.max(maxExpectedScore, 1)) * 100);
                healthScore = Math.min(100, Math.round(healthScore));
                
                // Update gauge data
                charts.healthGauge.data.datasets[0].data = [healthScore, 100 - healthScore];
                charts.healthGauge.data.datasets[0].backgroundColor[0] = 
                    healthScore >= 80 ? '#28a745' : healthScore >= 50 ? '#ffc107' : '#dc3545';
                charts.healthGauge.update('none');
                
                // Update text
                const healthValueEl = document.getElementById('healthValue');
                if (healthValueEl) {
                    healthValueEl.textContent = healthScore;
                    healthValueEl.style.color = healthScore >= 80 ? '#28a745' : healthScore >= 50 ? '#ffc107' : '#dc3545';
                }
            }
            
            // Collect detailed stats from visible issues in #files section
            const visibleIssues = document.querySelectorAll('#files .issue:not(.hidden-by-filter)');
            const filesWithIssues = new Map(); // fileName -> {errors, warnings, infos}
            const rulesTriggered = new Map(); // ruleId -> {name, errors, warnings, infos}
            const categoriesAffected = new Map(); // category -> {errors, warnings, infos}
            
            visibleIssues.forEach(issue => {
                // Get file name from parent file-section
                const fileSection = issue.closest('.file-section');
                const fileName = fileSection ? (fileSection.querySelector('.file-path-link')?.textContent || 'unknown') : 'unknown';
                
                if (!filesWithIssues.has(fileName)) {
                    filesWithIssues.set(fileName, { errors: 0, warnings: 0, infos: 0 });
                }
                
                // Get rule ID and name from data attributes (cleaner than parsing text)
                const ruleId = issue.dataset.ruleId || 'UNKNOWN';
                const ruleName = issue.dataset.ruleName || ruleId;
                
                if (!rulesTriggered.has(ruleId)) {
                    rulesTriggered.set(ruleId, { name: ruleName, errors: 0, warnings: 0, infos: 0 });
                }
                
                // Determine category from rule ID prefix
                let category = 'OTHER';
                if (ruleId.startsWith('BESTPRACTICE')) category = 'BESTPRACTICE';
                else if (ruleId.startsWith('METADATA')) category = 'METADATA';
                else if (ruleId.startsWith('NAMING')) category = 'NAMING';
                else if (ruleId.startsWith('TASK')) category = 'TASK';
                else if (ruleId.startsWith('VAR')) category = 'VARIABLES';
                else if (ruleId.startsWith('LIFECYCLE')) category = 'LIFECYCLE';
                else if (ruleId.startsWith('URI')) category = 'URI';
                else if (ruleId.startsWith('PYTHON')) category = 'PYTHON';
                else if (ruleId.startsWith('SYSTEMD')) category = 'SYSTEMD';
                else if (ruleId.startsWith('STYLE')) category = 'STYLE';
                
                if (!categoriesAffected.has(category)) {
                    categoriesAffected.set(category, { errors: 0, warnings: 0, infos: 0 });
                }
                
                // Update counts based on severity
                if (issue.classList.contains('error')) {
                    categoriesAffected.get(category).errors++;
                    rulesTriggered.get(ruleId).errors++;
                    filesWithIssues.get(fileName).errors++;
                } else if (issue.classList.contains('warning')) {
                    categoriesAffected.get(category).warnings++;
                    rulesTriggered.get(ruleId).warnings++;
                    filesWithIssues.get(fileName).warnings++;
                } else if (issue.classList.contains('info')) {
                    categoriesAffected.get(category).infos++;
                    rulesTriggered.get(ruleId).infos++;
                    filesWithIssues.get(fileName).infos++;
                }
            });
            
            const totalIssues = errors + warnings + infos;
            const filesCount = filesWithIssues.size;
            const rulesCount = rulesTriggered.size;
            const categoriesCount = categoriesAffected.size;
            const avgIssuesPerFile = filesCount > 0 ? (totalIssues / filesCount).toFixed(1) : '0.0';
            const errorRate = totalIssues > 0 ? ((errors / totalIssues) * 100).toFixed(1) + '%' : '0.0%';
            
            // Update all Quick Stats
            const qsTotal = document.getElementById('qs-total-issues');
            const qsFiles = document.getElementById('qs-files-with-issues');
            const qsRules = document.getElementById('qs-rules-triggered');
            const qsCategories = document.getElementById('qs-categories-affected');
            const qsAvg = document.getElementById('qs-avg-issues-file');
            const qsErrorRate = document.getElementById('qs-error-rate');
            
            if (qsTotal) qsTotal.textContent = totalIssues;
            if (qsFiles) qsFiles.textContent = filesCount;
            if (qsRules) qsRules.textContent = rulesCount;
            if (qsCategories) qsCategories.textContent = categoriesCount;
            if (qsAvg) qsAvg.textContent = avgIssuesPerFile;
            if (qsErrorRate) qsErrorRate.textContent = errorRate;
            
            // Update Category Bar Chart
            if (charts.categoryBar && categoriesAffected.size > 0) {
                const catLabels = Array.from(categoriesAffected.keys());
                const catErrors = catLabels.map(c => categoriesAffected.get(c).errors);
                const catWarnings = catLabels.map(c => categoriesAffected.get(c).warnings);
                const catInfos = catLabels.map(c => categoriesAffected.get(c).infos);
                
                charts.categoryBar.data.labels = catLabels;
                charts.categoryBar.data.datasets[0].data = catErrors;
                charts.categoryBar.data.datasets[1].data = catWarnings;
                charts.categoryBar.data.datasets[2].data = catInfos;
                charts.categoryBar.update('none');
            } else if (charts.categoryBar && categoriesAffected.size === 0) {
                charts.categoryBar.data.labels = [];
                charts.categoryBar.data.datasets[0].data = [];
                charts.categoryBar.data.datasets[1].data = [];
                charts.categoryBar.data.datasets[2].data = [];
                charts.categoryBar.update('none');
            }
            
            // Update Top Rules Chart with severity breakdown
            if (charts.topRules) {
                // Sort rules by total count and take top 15
                const sortedRules = Array.from(rulesTriggered.entries())
                    .map(([id, data]) => ({
                        id,
                        name: data.name,
                        errors: data.errors,
                        warnings: data.warnings,
                        infos: data.infos,
                        total: data.errors + data.warnings + data.infos
                    }))
                    .sort((a, b) => b.total - a.total)
                    .slice(0, 15);
                
                const ruleLabels = sortedRules.map(r => r.id);
                const ruleErrors = sortedRules.map(r => r.errors);
                const ruleWarnings = sortedRules.map(r => r.warnings);
                const ruleInfos = sortedRules.map(r => r.infos);
                
                // Store rule names and totals for tooltips
                charts.topRules.filteredRuleData = sortedRules;
                
                charts.topRules.data.labels = ruleLabels;
                charts.topRules.data.datasets[0].data = ruleErrors;
                charts.topRules.data.datasets[1].data = ruleWarnings;
                charts.topRules.data.datasets[2].data = ruleInfos;
                
                // Update tooltip callbacks to use filtered data
                charts.topRules.options.plugins.tooltip.callbacks.title = function(context) {
                    const idx = context[0].dataIndex;
                    const ruleData = charts.topRules.filteredRuleData[idx];
                    return ruleData ? `${ruleData.id}: ${ruleData.name}` : context[0].label;
                };
                charts.topRules.options.plugins.tooltip.callbacks.afterTitle = function(context) {
                    const idx = context[0].dataIndex;
                    const ruleData = charts.topRules.filteredRuleData[idx];
                    return ruleData ? `Total: ${ruleData.total} issues` : '';
                };
                
                charts.topRules.update('none');
            }
            
            // Update Top Files Chart with severity breakdown
            if (charts.topFiles) {
                // Sort files by total count and take top 10
                const sortedFiles = Array.from(filesWithIssues.entries())
                    .map(([name, data]) => ({
                        name: name.split('/').pop() || name,  // Get just filename
                        errors: data.errors,
                        warnings: data.warnings,
                        infos: data.infos,
                        total: data.errors + data.warnings + data.infos
                    }))
                    .sort((a, b) => b.total - a.total)
                    .slice(0, 10);
                
                const fileLabels = sortedFiles.map(f => f.name);
                const fileErrors = sortedFiles.map(f => f.errors);
                const fileWarnings = sortedFiles.map(f => f.warnings);
                const fileInfos = sortedFiles.map(f => f.infos);
                
                // Store file data for tooltips
                charts.topFiles.filteredFileData = sortedFiles;
                
                charts.topFiles.data.labels = fileLabels;
                charts.topFiles.data.datasets[0].data = fileErrors;
                charts.topFiles.data.datasets[1].data = fileWarnings;
                charts.topFiles.data.datasets[2].data = fileInfos;
                
                // Update tooltip callbacks to use filtered data
                charts.topFiles.options.plugins.tooltip.callbacks.afterTitle = function(context) {
                    const idx = context[0].dataIndex;
                    const fileData = charts.topFiles.filteredFileData[idx];
                    return fileData ? `Total: ${fileData.total} issues` : '';
                };
                
                charts.topFiles.update('none');
            }
        }
        
        // Initialize charts when tab is clicked or if already on statistics tab
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.dataset.tab === 'statistics') {
                    setTimeout(initializeCharts, 100);
                }
            });
        });
        
        // Also check on page load if statistics is the default tab
        if (document.querySelector('.tab-btn[data-tab="statistics"].active')) {
            setTimeout(initializeCharts, 100);
        }
    </script>"""
