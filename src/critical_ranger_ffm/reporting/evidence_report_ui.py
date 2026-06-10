from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from critical_ranger_ffm.reporting.paired_signal_report import (
    PairedSignalReport,
    build_fixture_signal_rows,
)


DEFAULT_OUTPUT_NAME = "evidence-report-ui.html"


def render_fixture_evidence_report_ui() -> str:
    """Return a static, fixture-only evidence report UI prototype."""
    rows = build_fixture_signal_rows(valid_pairs=8, invalid_pairs=2)
    report = PairedSignalReport.from_fixture_rows(rows)
    summary = report.to_json_dict()
    grid_cells = _build_fixture_grid(rows)
    fixture_payload = {
        "boundary": "FIXTURE SAMPLE — NOT EVIDENCE",
        "rows": rows,
        "summary": summary,
        "grid": grid_cells,
    }
    return _html_document(fixture_payload)


def write_fixture_evidence_report_ui(output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / DEFAULT_OUTPUT_NAME
    output_path.write_text(render_fixture_evidence_report_ui(), encoding="utf-8")
    return output_path


def _build_fixture_grid(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    highlighted = {(int(row["treatment_row"]), int(row["treatment_col"])) for row in rows if row["valid_pair"] == "true"}
    controls = {(int(row["control_row"]), int(row["control_col"])) for row in rows if row["valid_pair"] == "true"}
    cells: list[dict[str, Any]] = []
    for row in range(8):
        for col in range(8):
            if (row, col) in highlighted:
                state = "ranger_intervention"
            elif (row, col) in controls:
                state = "matched_control"
            elif (row + col) % 11 == 0:
                state = "burning"
            elif (row * 3 + col * 5) % 7 in {0, 1}:
                state = "empty"
            else:
                state = "tree"
            cells.append({"row": row, "col": col, "state": state})
    return cells


def _html_document(payload: dict[str, Any]) -> str:
    encoded_payload = json.dumps(payload, sort_keys=True)
    summary = payload["summary"]
    rows = payload["rows"]
    metric_cards = [
        ("valid_pairs", summary["valid_pairs"]),
        ("attempted_pairs", summary["attempted_pairs"]),
        ("invalid_rate", f"{summary['invalid_rate']:.1%}"),
        ("mean_burned_area_avoided", f"{summary['mean_burned_area_avoided']:.2f}"),
        ("density_match_diagnostics", "exact tercile fixture"),
        ("runner_invariant_status", summary["runner_invariant_status"]),
        ("replay_status", summary["replay_status"]),
        ("readout_horizon_steps", summary["readout_horizon_steps"]),
        ("evidence_label", summary["evidence_label"]),
    ]
    cards_html = "\n".join(
        f'<article class="metric-card"><span>{escape(label)}</span><strong>{escape(str(value))}</strong></article>'
        for label, value in metric_cards
    )
    seed_buttons = "\n".join(
        f'<button type="button" data-seed-button="{escape(str(seed))}">seed {escape(str(seed))}</button>'
        for seed in summary["seed_schedule"]["seeds"]
    )
    rows_html = "\n".join(
        "<tr>"
        f"<td>{escape(row['pair_id'])}</td>"
        f"<td>{escape(row['seed'])}</td>"
        f"<td>{escape(row['match_quality'])}</td>"
        f"<td>{escape(row['burned_area_avoided_delta'])}</td>"
        f"<td>{escape(row['valid_pair'])}</td>"
        "</tr>"
        for row in rows[:6]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Critical Ranger FFM evidence report prototype</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #061018;
      --panel: rgba(13, 28, 42, 0.88);
      --panel-strong: rgba(20, 43, 62, 0.96);
      --cyan: #46e5ff;
      --orange: #ff9d4d;
      --green: #73ff9f;
      --red: #ff5f6d;
      --muted: #8ca7b7;
      --line: rgba(70, 229, 255, 0.2);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 20% 10%, rgba(70, 229, 255, 0.14), transparent 34rem),
        radial-gradient(circle at 80% 0%, rgba(255, 157, 77, 0.12), transparent 32rem),
        linear-gradient(135deg, #03070b, var(--bg));
      color: #edfaff;
    }}
    .shell {{ padding: 28px; display: grid; gap: 20px; }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.6fr);
      gap: 18px;
      align-items: stretch;
    }}
    .panel {{
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--panel);
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.36), inset 0 1px rgba(255, 255, 255, 0.05);
      overflow: hidden;
    }}
    .hero-main {{ padding: 26px; position: relative; }}
    .kicker {{ color: var(--cyan); text-transform: uppercase; letter-spacing: 0.18em; font-size: 12px; font-weight: 800; }}
    h1 {{ margin: 10px 0 10px; font-size: clamp(34px, 5vw, 72px); line-height: 0.94; }}
    .boundary {{ color: #071018; background: var(--orange); display: inline-flex; padding: 8px 12px; border-radius: 999px; font-weight: 900; }}
    .subcopy {{ color: #b8ceda; max-width: 72ch; line-height: 1.55; }}
    .lab-notes {{ padding: 20px; display: grid; gap: 12px; }}
    .lab-notes strong {{ color: var(--green); }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }}
    button {{
      border: 1px solid rgba(70, 229, 255, 0.35);
      background: rgba(70, 229, 255, 0.08);
      color: #eefbff;
      border-radius: 999px;
      padding: 9px 12px;
      cursor: pointer;
      font-weight: 700;
    }}
    button[aria-pressed="true"], button:hover {{ border-color: var(--cyan); box-shadow: 0 0 24px rgba(70, 229, 255, 0.22); }}
    .layout {{ display: grid; grid-template-columns: minmax(320px, 1fr) minmax(320px, 0.85fr); gap: 20px; }}
    .viewport-wrap {{ padding: 18px; }}
    .viewport-title {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; color: var(--muted); margin-bottom: 14px; }}
    #grid-viewport {{
      min-height: 560px;
      border-radius: 20px;
      padding: 16px;
      background: linear-gradient(180deg, rgba(5, 18, 28, 0.9), rgba(2, 8, 13, 0.92));
      border: 1px solid rgba(255, 255, 255, 0.08);
      display: grid;
      grid-template-columns: repeat(8, minmax(28px, 1fr));
      gap: 8px;
    }}
    .cell {{
      aspect-ratio: 1;
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: inset 0 1px rgba(255, 255, 255, 0.08);
      transition: transform 220ms ease, filter 220ms ease;
    }}
    .animating .cell {{ animation: pulse 1.8s ease-in-out infinite alternate; }}
    .tree {{ background: linear-gradient(135deg, #174b34, #4ffc8b); }}
    .empty {{ background: linear-gradient(135deg, #0f1c24, #2c4250); }}
    .burning {{ background: linear-gradient(135deg, #5a1519, #ff5f6d); }}
    .ranger_intervention {{ background: linear-gradient(135deg, #0f4d5c, #46e5ff); box-shadow: 0 0 24px rgba(70, 229, 255, 0.45); }}
    .matched_control {{ background: linear-gradient(135deg, #5f3711, #ff9d4d); box-shadow: 0 0 24px rgba(255, 157, 77, 0.35); }}
    @keyframes pulse {{ from {{ filter: saturate(0.82); transform: scale(0.98); }} to {{ filter: saturate(1.18); transform: scale(1.02); }} }}
    .side-panels {{ display: grid; gap: 20px; }}
    #signal-panel, #report-panel {{ padding: 18px; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
    .metric-card {{ padding: 14px; border-radius: 16px; background: rgba(255, 255, 255, 0.045); border: 1px solid rgba(255, 255, 255, 0.08); }}
    .metric-card span {{ display: block; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
    .metric-card strong {{ display: block; margin-top: 6px; color: #fff; font-size: 18px; overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; color: #dbeef6; }}
    th, td {{ border-bottom: 1px solid rgba(255,255,255,0.08); padding: 8px 6px; text-align: left; }}
    th {{ color: var(--cyan); font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; }}
    .footer-boundary {{ color: var(--muted); line-height: 1.5; padding: 18px; }}
    @media (max-width: 940px) {{ .hero, .layout {{ grid-template-columns: 1fr; }} #grid-viewport {{ min-height: 380px; }} }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="panel hero-main">
        <div class="kicker">dark simulation lab / fixture UI</div>
        <h1>Critical Ranger FFM evidence report prototype</h1>
        <p class="boundary">FIXTURE SAMPLE — NOT EVIDENCE</p>
        <p class="subcopy">This browser prototype uses generated fixture/sample data only. It is evidence presentation design for reviewing report shape, not evidence generation, not a gate result, and not a scientific conclusion.</p>
        <div class="controls" aria-label="Seed/config controls">
          <button type="button" id="animation-toggle" aria-pressed="false">Animation toggle</button>
          {seed_buttons}
        </div>
      </div>
      <aside class="panel lab-notes">
        <div><strong>Seed/config controls</strong><br />Visible controls expose fixture seed slices and config state.</div>
        <div><strong>Large grid viewport</strong><br />The forest board stays dominant so the switch-point story is spatial first.</div>
        <div><strong>Side-by-side signal and report panels</strong><br />Metrics and row details sit next to the simulated board for review.</div>
        <div><strong>No real experiment output is loaded or required</strong><br />The UI cannot replace paired evidence gates.</div>
      </aside>
    </section>

    <section class="layout">
      <section class="panel viewport-wrap">
        <div class="viewport-title"><strong>Large grid viewport</strong><span id="active-seed-label">all fixture seeds</span></div>
        <div id="grid-viewport" role="img" aria-label="Fixture forest grid with ranger intervention and matched control cells"></div>
      </section>
      <section class="side-panels">
        <div class="panel" id="signal-panel">
          <h2>Signal panel</h2>
          <div class="metric-grid">{cards_html}</div>
        </div>
        <div class="panel" id="report-panel">
          <h2>Report-contract field sample</h2>
          <table>
            <thead><tr><th>pair</th><th>seed</th><th>match</th><th>delta</th><th>valid</th></tr></thead>
            <tbody id="row-table">{rows_html}</tbody>
          </table>
        </div>
      </section>
    </section>

    <section class="panel footer-boundary">
      UI boundary: fixture-only presentation. This prototype displays paired CSV/Markdown/JSON contract fields without inventing stronger claims. Future real runs must still pass the explicit evidence gates before anyone treats output as more than smoke/signal review.
    </section>
  </main>
  <script>
    window.CRITICAL_RANGER_FFM_FIXTURE_UI = {encoded_payload};
    const fixtureRows = window.CRITICAL_RANGER_FFM_FIXTURE_UI.rows;
    const fixtureSummary = window.CRITICAL_RANGER_FFM_FIXTURE_UI.summary;
    const gridCells = window.CRITICAL_RANGER_FFM_FIXTURE_UI.grid;
    const viewport = document.getElementById('grid-viewport');
    const label = document.getElementById('active-seed-label');

    function renderGrid(seed) {{
      viewport.replaceChildren();
      const activeRows = seed ? fixtureRows.filter((row) => row.seed === String(seed)) : fixtureRows;
      const activeCoords = new Set(activeRows.map((row) => `${{row.treatment_row}}:${{row.treatment_col}}`));
      gridCells.forEach((cell) => {{
        const div = document.createElement('div');
        const key = `${{cell.row}}:${{cell.col}}`;
        const state = activeCoords.has(key) ? 'ranger_intervention' : cell.state;
        div.className = `cell ${{state}}`;
        div.title = `row ${{cell.row}}, col ${{cell.col}} — ${{state}}`;
        viewport.appendChild(div);
      }});
      label.textContent = seed ? `fixture seed ${{seed}}` : 'all fixture seeds';
    }}

    document.querySelectorAll('[data-seed-button]').forEach((button) => {{
      button.addEventListener('click', () => {{
        document.querySelectorAll('[data-seed-button]').forEach((item) => item.setAttribute('aria-pressed', 'false'));
        button.setAttribute('aria-pressed', 'true');
        renderGrid(button.dataset.seedButton);
      }});
    }});

    document.getElementById('animation-toggle').addEventListener('click', (event) => {{
      const pressed = event.currentTarget.getAttribute('aria-pressed') === 'true';
      event.currentTarget.setAttribute('aria-pressed', String(!pressed));
      viewport.classList.toggle('animating', !pressed);
    }});

    renderGrid(null);
  </script>
</body>
</html>
"""
