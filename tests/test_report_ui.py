"""HTML report states and reproducible browser fixtures.

Copyright (c) 2026 OpenAI

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

import json
from pathlib import Path
import re

import pytest

from bake_linter.core.models import LintResult, LintSummary, Severity
from bake_linter.core.oelint_integration import OelintResult, OelintSummary
from bake_linter.core.registry import get_registry
from bake_linter.output.html import HtmlFormatter
from bake_linter.output.html_oelint import OelintHtmlFormatter


CASES = {
    'mixed': ([1, 1, 1], 2, 'error', 'error-highlight'),
    'zero': ([0, 2, 1], 2, 'warning', 'success-highlight'),
    'clean': ([0, 0, 0], 2, 'success', 'success-highlight'),
    'unscanned': ([0, 0, 0], 0, 'neutral', 'neutral-highlight'),
    'info': ([0, 0, 1], 2, 'info', 'success-highlight'),
    'incomplete': ([0, 0, 0], 2, 'error', 'neutral-highlight'),
}


def render_case(tool, case):
    get_registry().discover_rules()
    counts, files, _, _ = CASES[case]
    results = []
    for severity, count in zip(['error', 'warning', 'info'], counts):
        for index in range(count):
            path = Path('recipes/example.bb')
            if tool == 'bake':
                results.append(LintResult(
                    rule_id='BESTPRACTICE001', file=path, line=index + 1,
                    severity=Severity.from_string(severity), message='Example ' + severity,
                    rule_name='Example rule',
                ))
            else:
                results.append(OelintResult(
                    file=path, line=index + 1, severity=severity,
                    rule_id='oelint.vars.example', message='Example ' + severity,
                ))
    if tool == 'bake':
        summary = LintSummary.from_results(results, files_scanned=files, rules_executed=110)
        if case == 'incomplete':
            summary.runtime_errors = ['Example failure']
        formatter = HtmlFormatter()
    else:
        summary = OelintSummary.from_results(results, files_scanned=files)
        formatter = OelintHtmlFormatter()
        # Keep browser fixtures independent of oelint installation and network access.
        formatter._get_rule_docs_data = lambda _: json.dumps({'oelint.vars.example': '# Example rule'})
    return formatter.format_results(results, summary)


@pytest.mark.parametrize('tool,case', [
    (tool, case) for tool in ['bake', 'oelint'] for case in CASES
    if not (tool == 'oelint' and case == 'incomplete')
])
def test_initial_report_status(tool, case):
    rendered = render_case(tool, case)
    _, _, status, rate_class = CASES[case]
    assert f'<section class="summary {status}">' in rendered
    assert f'class="quick-stat {rate_class}"' in rendered
    if case == 'unscanned':
        assert 'No files scanned' in rendered
        assert '✓ No issues found' not in rendered
    if case == 'incomplete':
        assert 'Analysis incomplete' in rendered
        assert '✓ No issues found' not in rendered
    chart_data = json.loads(re.search(
        r'<script id="chart-data" type="application/json">(.*?)</script>', rendered, re.S,
    ).group(1))
    assert chart_data['analysisIncomplete'] == (case == 'incomplete')
    if tool == 'bake' and chart_data['totalIssues']:
        assert chart_data['ruleCategories']['BESTPRACTICE001'] == 'BEST_PRACTICES'


if __name__ == '__main__':
    import sys

    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=True)
    for tool in ['bake', 'oelint']:
        for case in CASES:
            if tool == 'oelint' and case == 'incomplete':
                continue
            (target / f'{tool}-{case}.html').write_text(render_case(tool, case), encoding='utf-8')
