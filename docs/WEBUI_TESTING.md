# HTML report browser checks

The Python suite checks initial report states. The browser checks also exercise
severity filtering before chart creation, overall versus filtered statistics,
empty and incomplete analyses, unavailable charts, keyboard use of rule help,
and a 390px mobile viewport. They cover both report formatters.

Install Playwright in a temporary directory and generate local fixtures:

```sh
npm install --prefix /tmp/bake-ui-tools playwright
PYTHONPATH=. python tests/test_report_ui.py /tmp/bake-ui-review
curl -fsSL https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js \
  -o /tmp/bake-chart.umd.js
NODE_PATH=/tmp/bake-ui-tools/node_modules \
CHROME_EXECUTABLE=/usr/bin/google-chrome \
  node tests/webui_browser.cjs /tmp/bake-ui-review /tmp/bake-chart.umd.js
```

Set `CHROME_EXECUTABLE` to an installed Chromium-compatible browser, or omit it
when Playwright's Chromium is installed. Chart requests are intercepted: one
pass serves the supplied local Chart.js file and another blocks it. No report
content is sent to a server. Screenshots are saved beside the fixtures.
