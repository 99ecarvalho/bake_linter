"""Shared status semantics for the HTML reports.

Copyright (c) 2026 OpenAI

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""


def summary_status(summary):
    if getattr(summary, 'runtime_errors', []) or getattr(summary, 'skipped_files', []):
        return 'error', 'Analysis incomplete'
    if not summary.files_scanned:
        return 'neutral', 'No files scanned'
    if summary.errors:
        return 'error', f'{summary.total_issues} Issue(s) Found'
    if summary.warnings:
        return 'warning', f'{summary.total_issues} Issue(s) Found'
    if summary.infos:
        return 'info', f'{summary.infos} Informational Finding(s)'
    return 'success', 'All Clear!'


def empty_report_message(summary):
    if not summary.files_scanned:
        return '<p class="no-data">No files were scanned.</p>'
    if getattr(summary, 'runtime_errors', []) or getattr(summary, 'skipped_files', []):
        if not summary.total_issues:
            return '<p class="no-data">Analysis incomplete. Findings may be missing.</p>'
    return ''


def error_rate_class(summary):
    if not summary.files_scanned or getattr(summary, 'runtime_errors', []) or getattr(summary, 'skipped_files', []):
        return 'neutral-highlight'
    return 'error-highlight' if summary.errors else 'success-highlight'


REPORT_STYLES = """<style>
.quick-stat.success-highlight { background: linear-gradient(135deg, #d4edda, #c3e6cb); }
.success-highlight .qs-value { color: #155724; }
.error-highlight .qs-value { color: #842029; }
.quick-stat.neutral-highlight { background: #e9ecef; }
.neutral-highlight .qs-value, .stat.zero .stat-value { color: #495057; }
.summary.neutral { background: #e9ecef; }
.status-badge.neutral { background: #495057; color: white; }
.summary.info { background: #d1ecf1; }
.status-badge.info { background: #0c5460; color: white; }
.filter-status, .chart-unavailable, .filter-empty { padding: 12px 16px; color: #495057; }
.filter-empty { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }
[hidden], .issue-marker.hidden-by-filter { display: none !important; }
button:focus-visible, a:focus-visible, summary:focus-visible { outline: 3px solid #334caa; outline-offset: 3px; }
.chart-card, .quick-stat { min-width: 0; }
@media (max-width: 600px) {
    .stats-grid { grid-template-columns: minmax(0, 1fr); }
    .chart-card.wide { grid-column: auto; }
    .file-path, .file-path-link { overflow-wrap: anywhere; }
}
</style>"""

REPORT_SCRIPT = """<script>
// Numerical summaries work independently of the optional chart library.
function updateReportState(errors, warnings, infos) {
    const data = JSON.parse(document.getElementById('chart-data').textContent);
    const total = errors + warnings + infos;
    const filtered = document.querySelectorAll('.filter-btn.active').length !== 3;
    document.querySelectorAll('.filter-btn').forEach(button => {
        button.setAttribute('aria-pressed', String(button.classList.contains('active')));
    });
    const note = document.getElementById('filter-status');
    note.textContent = 'Showing ' + total + ' of ' + data.totalIssues +
        ' findings. Summary and health score describe the full analysis.';
    document.querySelectorAll('.filter-empty').forEach(element => {
        element.hidden = !(filtered && total === 0 && data.totalIssues > 0);
    });
    const rate = document.getElementById('qs-error-rate');
    const card = rate.closest('.quick-stat');
    const errorsShown = document.querySelector('.filter-btn[data-severity="error"]').classList.contains('active');
    const unknown = !errorsShown || !data.filesScanned || data.analysisIncomplete;
    const percentage = total ? errors / total * 100 : 0;
    rate.textContent = unknown ? '—' : percentage > 0 && percentage < 0.1 ? '<0.1%' : percentage.toFixed(1) + '%';
    card.classList.remove('error-highlight', 'success-highlight', 'neutral-highlight');
    card.classList.add(unknown ? 'neutral-highlight' : errors ? 'error-highlight' : 'success-highlight');
    card.title = !errorsShown ? 'Errors are hidden by the severity filter.' :
        data.analysisIncomplete ? 'Analysis did not complete.' :
        !data.filesScanned ? 'No files were scanned.' : 'Percentage of visible findings that are errors.';

    const health = document.getElementById('healthValue');
    const score = Math.max(0, Math.min(100, Math.round(100 -
        (data.errors * 10 + data.warnings * 3 + data.infos) / Math.max(data.filesScanned * 50, 1) * 100)));
    health.textContent = !data.filesScanned || data.analysisIncomplete ? '—' : score;
    health.style.color = !data.filesScanned || data.analysisIncomplete ? '#495057' :
        score >= 80 ? '#155724' : score >= 50 ? '#856404' : '#842029';
    document.querySelectorAll('#files .file-section, .rule-file-section, .rule-section, .category-section').forEach(section => {
        const badges = section.querySelector(':scope > summary .file-badges, :scope > summary .category-badges, :scope > summary .rule-count');
        if (!badges) return;
        badges.querySelectorAll('.badge').forEach(badge => badge.remove());
        ['info', 'warning', 'error'].forEach(severity => {
            const count = section.querySelectorAll('.issue.' + severity + ':not(.hidden-by-filter)').length;
            if (count) {
                const badge = document.createElement('span');
                badge.className = 'badge ' + severity;
                badge.textContent = count + ' ' + severity[0].toUpperCase();
                badges.prepend(badge);
            }
        });
    });
    const chartsAvailable = typeof Chart !== 'undefined';
    document.getElementById('chart-unavailable').hidden = chartsAvailable;
    document.getElementById('healthGauge').hidden = !data.filesScanned || data.analysisIncomplete;
    document.querySelectorAll('.chart-card').forEach(card => {
        if (!card.querySelector('.quick-stats, .health-score-container')) card.hidden = !chartsAvailable;
    });
}
document.addEventListener('keydown', event => {
    const modal = document.getElementById('rule-docs-modal');
    if (!modal || !(modal.classList.contains('active') || modal.classList.contains('show'))) return;
    if (event.key === 'Escape') {
        closeRuleDocsModal();
    } else if (event.key === 'Tab') {
        const focusable = Array.from(modal.querySelectorAll('button, a[href], [tabindex="0"]'));
        const first = focusable[0], last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault(); first.focus();
        }
    }
});
</script>"""
