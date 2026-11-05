"""The cross-agent benchmark report, built from recorded iterations. See docs/reference/evals.md.

build() is a pure function of a skill's iterations, oldest first. Every value
it reports carries a state, so data that is missing or does not apply is
never shown, compared or averaged as a 0. render_html() lays the reports out
as one self-contained page: inline CSS, no script and no network.
"""

import html
from typing import TYPE_CHECKING, Any

from skills_tooling.evals.adapter import AGENTS
from skills_tooling.evals.benchmark import DELTA_METRICS, METRICS, MIN_SPREAD_N
from skills_tooling.evals.history import UNRECORDED

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

DEFAULT_THRESHOLD = 0.1
POOLED = "all cases"
# Metrics the grader's verdicts feed, and the deltas of those metrics.
GRADED = ("graded_pass_rate", "outcome_pass_rate")
# A fall must exceed the threshold by more than float noise.
EPSILON = 1e-9
STATES = {
    "not_run": "not run",
    "case_absent": "case not run",
    "no_scored": "no scored trials",
    "not_applicable": "n/a",
    "baseline_off": "no baseline",
    "no_data": "no data",
}
MEANINGS = {
    "not_run": "the agent was not run in that iteration",
    "case_absent": "the agent's run did not include the case",
    "no_scored": "every trial was excluded (infrastructure error, contamination or a secret)",
    "not_applicable": "the case has nothing of that kind to measure",
    "baseline_off": "the run had no baseline arm",
    "no_data": "trials were scored but none measured this, such as when every grading failed",
}

type Value = dict[str, Any]


def _state(state: str) -> Value:
    return {"state": state}


def _stat(metric: Mapping[str, Any]) -> Value:
    return {
        "state": "value",
        "mean": metric["mean"],
        "stddev": metric["stddev"],
        "n": metric["n"],
    }


# ------------------------------------------------------------- extraction ---


def _arm_value(arm: Mapping[str, Any], metric: str, has_expectations: bool) -> Value:
    """One skill-arm metric of one case."""
    measured = arm["metrics"][metric]
    if isinstance(measured, dict):
        return _stat(measured)
    if measured == "not_applicable":
        return _state("not_applicable")
    if arm["n_scored"] == 0:
        return _state("no_scored")
    # Scored trials and no value: a grader-fed metric lost every verdict to grader
    # errors, or the case has nothing of that kind to measure.
    if metric in GRADED and has_expectations:
        return _state("no_data")
    return _state("not_applicable")


def _case_delta(
    run: Mapping[str, Any], case: Mapping[str, Any], metric: str, skill: Value
) -> Value:
    if not run["baseline"]:
        return _state("baseline_off")
    delta = case["delta"]
    if not delta:
        # The baseline ran without this case: there was nothing for it to measure.
        return _state("not_applicable")
    measured = delta[metric]
    if measured["value"] is None:
        if skill["state"] in {"not_applicable", "no_scored"}:
            return _state(skill["state"])
        baseline = case["baseline"]
        if isinstance(baseline, dict) and baseline["n_scored"] == 0:
            return _state("no_scored")
        return _state("no_data")
    return {
        "state": "value",
        "mean": measured["value"],
        "stddev": None,
        "n": measured["n_skill"],
        "n_baseline": measured["n_baseline"],
    }


def _case_values(run: Mapping[str, Any], case_id: str) -> dict[str, Value]:
    """Every metric and delta of one case in one run, keyed as the history keys them."""
    meta = next((c for c in run["cases"] if c["id"] == case_id), None)
    case = run["benchmark"]["cases"].get(case_id)
    if meta is None or case is None:
        return dict.fromkeys((*METRICS, *_deltas()), _state("case_absent"))
    has_expectations = bool(meta["expectations"])
    values = {m: _arm_value(case["skill"], m, has_expectations) for m in METRICS}
    for m in DELTA_METRICS:
        values[f"delta:{m}"] = _case_delta(run, case, m, values[m])
    return values


def _pooled_values(run: Mapping[str, Any]) -> dict[str, Value]:
    """The agent's metrics over all cases, and its delta: the mean of the per-case deltas."""
    cases = [_case_values(run, c["id"]) for c in run["cases"]]
    values: dict[str, Value] = {}
    for m in METRICS:
        measured = run["benchmark"]["pooled"]["skill"][m]
        values[m] = _stat(measured) if isinstance(measured, dict) else _missing(cases, m)
    for m in DELTA_METRICS:
        key = f"delta:{m}"
        measured = run["benchmark"]["delta"][m]
        if not run["baseline"]:
            values[key] = _state("baseline_off")
        elif measured["value"] is not None:
            values[key] = {
                "state": "value",
                "mean": measured["value"],
                "stddev": None,
                "n": measured["n_cases"],
                "unit": "cases",
            }
        else:
            values[key] = _missing(cases, key)
    return values


def _missing(cases: Sequence[Mapping[str, Value]], key: str) -> Value:
    """Why a figure over all cases has no value, from why each case has none."""
    states = {c[key]["state"] for c in cases}
    if states == {"not_applicable"}:
        return _state("not_applicable")
    if states and states <= {"not_applicable", "no_scored"}:
        return _state("no_scored")
    return _state("no_data")


def _deltas() -> tuple[str, ...]:
    return tuple(f"delta:{m}" for m in DELTA_METRICS)


def _values(run: Mapping[str, Any] | None, scope: str) -> dict[str, Value]:
    if run is None:
        return dict.fromkeys((*METRICS, *_deltas()), _state("not_run"))
    return _pooled_values(run) if scope == POOLED else _case_values(run, scope)


# ------------------------------------------------------------- comparison ---


def _differs(before: Any, after: Any, *, reported: bool = False) -> bool:  # noqa: ANN401
    """Whether two provenance values differ; a reported list empty on either side says nothing."""
    if reported and (not before or not after):
        return False
    return bool(before != after)


def _labels(before: Mapping[str, Any], after: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """What differs between two runs of one agent: (for every metric, for grader-fed ones only).

    A new skill version or commit is the change being measured, so it is no label.
    """
    old, new = before["provenance"], after["provenance"]
    every = []
    if _differs(old.get("evals_sha256"), new.get("evals_sha256")):
        every.append("cases or rubric changed")
    if _differs(old.get("requested_model"), new.get("requested_model")) or _differs(
        old.get("agent_models"), new.get("agent_models"), reported=True
    ):
        every.append("agent model changed")
    if _differs(old.get("agent_cli_versions"), new.get("agent_cli_versions"), reported=True):
        every.append("agent CLI version changed")
    graded = []
    if _differs(old.get("grader_prompt_sha256"), new.get("grader_prompt_sha256")):
        graded.append("grader prompt changed")
    if _differs(old.get("grader_model_requested"), new.get("grader_model_requested")) or _differs(
        old.get("grader_models"), new.get("grader_models"), reported=True
    ):
        graded.append("grader model changed")
    if _differs(old.get("grader_cli_versions"), new.get("grader_cli_versions"), reported=True):
        graded.append("grader CLI version changed")
    return every, graded


def _case_definition(run: Mapping[str, Any], case_id: str) -> dict[str, Any] | None:
    # in_baseline is left out: it follows the run's --baseline flag, not the case.
    meta = next((c for c in run["cases"] if c["id"] == case_id), None)
    if meta is None:
        return None
    return {k: meta[k] for k in ("kind", "should_trigger", "expectations")}


def _scope_labels(before: Mapping[str, Any], after: Mapping[str, Any], scope: str) -> list[str]:
    if scope == POOLED:
        ids = [[c["id"] for c in run["cases"]] for run in (before, after)]
        return ["case set changed"] if sorted(ids[0]) != sorted(ids[1]) else []
    changed = _case_definition(before, scope) != _case_definition(after, scope)
    return ["case changed"] if changed else []


def _case_labels(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
    """What changed in the cases between two runs, as the comparison's labels."""
    common = {c["id"] for c in before["cases"]} & {c["id"] for c in after["cases"]}
    redefined = any(_scope_labels(before, after, case_id) for case_id in sorted(common))
    return [*_scope_labels(before, after, POOLED), *(["case changed"] if redefined else [])]


def _thin(value: Value) -> bool:
    if value.get("unit") == "cases":
        return False
    return bool(min(value["n"], value.get("n_baseline", value["n"])) < MIN_SPREAD_N)


# ------------------------------------------------------------------ build ---


def _columns(iterations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": i["iteration"] if i["iteration"] is not None else UNRECORDED,
            "recorded": i["iteration"] is not None,
            "recorded_at": i["recorded_at"] if i["iteration"] is not None else None,
        }
        for i in iterations
    ]


def _unique(items: Iterator[str]) -> list[str]:
    return list(dict.fromkeys(items))


type Columns = list[dict[str, dict[str, Any]]]


def _history_rows(runs: Columns, agent: str, scopes: Sequence[str]) -> list[dict[str, Any]]:
    """Every series of the agent that has a value in at least one iteration."""
    rows = []
    for scope in scopes:
        per_column = [_values(column.get(agent), scope) for column in runs]
        for key in (*METRICS, *_deltas()):
            values = [v[key] for v in per_column]
            if any(v["state"] == "value" for v in values):
                rows.append({"scope": scope, "metric": key, "values": values})
    return rows


def _measured_cases(rows: Sequence[Mapping[str, Any]], metric: str, column: int) -> set[str]:
    """The cases with a value for the metric in one column."""
    return {
        r["scope"]
        for r in rows
        if r["metric"] == metric
        and r["scope"] != POOLED
        and r["values"][column]["state"] == "value"
    }


def _compare(
    runs: Columns,
    names: Sequence[str],
    agent: str,
    rows: Sequence[Mapping[str, Any]],
    threshold: float,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """The agent's last two benchmarks compared: what differs, and each fall beyond threshold."""
    # By when the agent's own run started: an iteration's runs can start days apart, so
    # the order of the iterations is not always the order of one agent's runs.
    # A run in two columns (recorded, then passed again with --run) counts once, at its
    # first column, or it would be compared with itself and hide a fall.
    first: dict[str, int] = {}
    for i, column in enumerate(runs):
        if agent in column:
            first.setdefault(column[agent]["run_id"], i)
    ran = sorted(first.values(), key=lambda i: (str(runs[i][agent]["started_at"]), i))
    if len(ran) < 2:  # noqa: PLR2004 -- a comparison needs two benchmarks
        return None, []
    b, a = ran[-2], ran[-1]
    before, after = runs[b][agent], runs[a][agent]
    every, graded = _labels(before, after)
    comparison = {
        "agent": agent,
        "from": names[b],
        "to": names[a],
        "labels": [*every, *graded, *_case_labels(before, after)],
    }
    regressions = []
    for row in rows:
        old, new = row["values"][b], row["values"][a]
        if old["state"] != "value" or new["state"] != "value":
            continue
        change = new["mean"] - old["mean"]
        if change >= -threshold - EPSILON:
            continue
        fed_by_grader = row["metric"].removeprefix("delta:") in GRADED
        labels = [
            *every,
            *(graded if fed_by_grader else []),
            *_scope_labels(before, after, row["scope"]),
        ]
        if row["scope"] == POOLED and _measured_cases(rows, row["metric"], b) != _measured_cases(
            rows, row["metric"], a
        ):
            # Same case list, but a case measured on one side only (all excluded, or every
            # grading failed) changes what the figure averages over.
            labels.append("measured over different cases")
        regressions.append(
            {
                "agent": agent,
                "scope": row["scope"],
                "metric": row["metric"],
                "from": names[b],
                "to": names[a],
                "before": old,
                "after": new,
                "change": change,
                "labels": labels,
                "comparable": not labels,
                "thin": _thin(old) or _thin(new),
            }
        )
    return comparison, regressions


def _matrix_cell(values: Mapping[str, Value]) -> dict[str, Value]:
    return {
        "trigger": values["trigger_accuracy"],
        "pass": values["outcome_pass_rate"],
        "delta": values["delta:outcome_pass_rate"],
    }


def _matrix_data(latest: Mapping[str, Mapping[str, Any]], agents: Sequence[str]) -> dict[str, Any]:
    """The agent x case matrix of the latest iteration, and each agent's figures over all cases."""
    meta = {c["id"]: c for r in latest.values() for c in r["cases"]}
    rows = [
        {
            "case": case_id,
            "kind": case["kind"],
            "should_trigger": case["should_trigger"],
            "cells": {a: _matrix_cell(_values(latest.get(a), case_id)) for a in agents},
        }
        for case_id, case in meta.items()
    ]
    pooled = {a: _matrix_cell(_values(latest.get(a), POOLED)) for a in agents}
    return {"rows": rows, "pooled": pooled}


def _provenance_row(name: str, run: Mapping[str, Any]) -> dict[str, Any]:
    p = run["provenance"]
    return {
        "iteration": name,
        "agent": run["agent"],
        "run_id": run["run_id"],
        "trials_per_case": run["trials_per_case"],
        "baseline": run["baseline"],
        "requested_model": p.get("requested_model"),
        "agent_models": p.get("agent_models", []),
        "agent_cli_versions": p.get("agent_cli_versions", []),
        "grader_model_requested": p.get("grader_model_requested"),
        "grader_models": p.get("grader_models", []),
        "grader_cli_versions": p.get("grader_cli_versions", []),
        "git_commit": p.get("git_commit"),
        "git_dirty": p.get("git_dirty"),
        "skill_sha256": p.get("skill_sha256"),
        "evals_sha256": p.get("evals_sha256"),
    }


def build(
    iterations: Sequence[Mapping[str, Any]], *, threshold: float = DEFAULT_THRESHOLD
) -> dict[str, Any]:
    """The report of one skill's iterations, oldest first; the last may be unrecorded."""
    if not iterations:
        msg = "no iterations to report"
        raise ValueError(msg)
    columns = _columns(iterations)
    names = [c["name"] for c in columns]
    runs: Columns = [{r["agent"]: r for r in i["runs"]} for i in iterations]
    # Every agent the harness runs, so one never benchmarked shows as not run.
    agents = sorted(set(AGENTS) | {agent for column in runs for agent in column})
    # Cases in the latest iteration first, then any that only earlier ones ran.
    case_ids = _unique(
        c["id"] for column in reversed(runs) for r in column.values() for c in r["cases"]
    )
    history = {agent: _history_rows(runs, agent, [POOLED, *case_ids]) for agent in agents}
    comparisons, regressions = [], []
    for agent in agents:
        comparison, found = _compare(runs, names, agent, history[agent], threshold)
        if comparison is not None:
            comparisons.append(comparison)
        regressions += found
    latest = runs[-1]
    pooled = {agent: _values(latest.get(agent), POOLED) for agent in agents}
    return {
        "skill": iterations[-1]["skill"],
        "threshold": threshold,
        "columns": columns,
        "agents": agents,
        "matrix": {"iteration": names[-1], **_matrix_data(latest, agents)},
        "deltas": {
            agent: {m: v[f"delta:{m}"] for m in DELTA_METRICS} for agent, v in pooled.items()
        },
        "provenance": [
            _provenance_row(name, column[agent])
            for name, column in zip(names, runs, strict=True)
            for agent in agents
            if agent in column
        ],
        "history": history,
        "comparisons": comparisons,
        "regressions": regressions,
    }


# ----------------------------------------------------------------- render ---


def show(value: Value) -> str:
    """A value as the report prints it: mean ± stddev (n), a signed delta, or its state."""
    if value["state"] != "value":
        return STATES[value["state"]]
    if "n_baseline" in value:
        return f"{value['mean']:+.2f} (n={value['n']}/{value['n_baseline']})"
    if value.get("unit") == "cases":
        return f"{value['mean']:+.2f} (cases={value['n']})"
    if value["stddev"] is None:
        return f"{value['mean']:.2f} (n={value['n']})"
    return f"{value['mean']:.2f} ± {value['stddev']:.2f} (n={value['n']})"


def describe(regression: Mapping[str, Any]) -> str:
    """One regression as a line of text."""
    caveats = list(regression["labels"])
    if regression["thin"]:
        caveats.append(f"thin sample (n < {MIN_SPREAD_N})")
    kind = "regression" if regression["comparable"] else "regression, not like-for-like"
    return (
        f"{regression['agent']} {regression['scope']} {regression['metric']}:"
        f" {show(regression['before'])} -> {show(regression['after'])}"
        f" ({regression['change']:+.2f}, {regression['from']} -> {regression['to']}; {kind}"
        + "".join(f"; {c}" for c in caveats)
        + ")"
    )


def summary(report: Mapping[str, Any]) -> str:
    """The text the command prints for one skill."""
    columns = ", ".join(c["name"] for c in report["columns"])
    lines = [f"{report['skill']}: {len(report['columns'])} iteration(s): {columns}"]
    if report["regressions"]:
        lines.append(f"Regressions beyond {report['threshold']:.2f}:")
        lines += [f"  {describe(r)}" for r in report["regressions"]]
    else:
        lines.append(f"No regression beyond {report['threshold']:.2f}.")
    return "\n".join(lines) + "\n"


def _md(text: object) -> str:
    """Text safe in a Markdown table cell: no pipe, no newline, no HTML tag."""
    escaped = str(text).replace("&", "&amp;").replace("<", "&lt;").replace("|", "\\|")
    return " ".join(escaped.split())


def _matrix_entries(report: Mapping[str, Any]) -> list[tuple[str, str, Mapping[str, Any]]]:
    """The matrix's rows: each case of the latest iteration, then the agents' figures over all."""
    entries = [
        (r["case"], "trigger" if r["should_trigger"] else "no trigger", r["cells"])
        for r in report["matrix"]["rows"]
    ]
    entries.append((POOLED, "", report["matrix"]["pooled"]))
    return entries


def markdown(report: Mapping[str, Any]) -> str:
    """The headline matrix and the regressions as Markdown, for a CI job summary."""
    head = ["case", "expects"]
    for agent in report["agents"]:
        head += [f"{agent} trigger", f"{agent} pass rate", f"{agent} Δ pass rate"]
    lines = [
        f"### {_md(report['skill'])}: iteration {_md(report['matrix']['iteration'])}",
        "",
        "| " + " | ".join(head) + " |",
        "|" + " --- |" * len(head),
    ]
    for case, expects, cells in _matrix_entries(report):
        values = [
            show(cells[agent][k])
            for agent in report["agents"]
            for k in ("trigger", "pass", "delta")
        ]
        lines.append("| " + " | ".join(_md(v) for v in [case, expects, *values]) + " |")
    lines.append("")
    if report["regressions"]:
        lines.append(f"Regressions beyond {report['threshold']:.2f}:")
        lines.append("")
        lines += [f"- {_md(describe(r))}" for r in report["regressions"]]
    else:
        lines.append(f"No regression beyond {report['threshold']:.2f}.")
    return "\n".join(lines) + "\n"


def _e(text: object) -> str:
    return html.escape(str(text), quote=True)


def _td(value: Value, *, flag: bool = False) -> str:
    classes = [value["state"] if value["state"] == "value" else "missing"]
    classes += ["regressed"] if flag else []
    return f'<td class="{" ".join(classes)}">{_e(show(value))}</td>'


def _table(head: Sequence[str], rows: Sequence[str]) -> str:
    header = "".join(f"<th>{_e(h)}</th>" for h in head)
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _matrix(report: Mapping[str, Any]) -> str:
    head = ["case", "expects"]
    for agent in report["agents"]:
        head += [f"{agent} trigger", f"{agent} pass rate", f"{agent} Δ pass rate"]
    rows = []
    for case, expects, cells in _matrix_entries(report):
        tds = "".join(
            _td(cells[agent][k])
            for agent in report["agents"]
            for k in ("trigger", "pass", "delta")
        )
        rows.append(f"<tr><th>{_e(case)}</th><td>{_e(expects)}</td>{tds}</tr>")
    return _table(head, rows)


def _deltas_table(report: Mapping[str, Any]) -> str:
    rows = [
        f"<tr><th>{_e(agent)}</th>"
        + "".join(_td(report["deltas"][agent][m]) for m in DELTA_METRICS)
        + "</tr>"
        for agent in report["agents"]
    ]
    return _table(["agent", *DELTA_METRICS], rows)


def _provenance(report: Mapping[str, Any]) -> str:
    def listed(values: Sequence[str]) -> str:
        return ", ".join(values) if values else "not reported"

    rows = []
    for p in report["provenance"]:
        commit = (p["git_commit"] or "unknown")[:12] + (" (dirty)" if p["git_dirty"] else "")
        cells = [
            p["iteration"],
            p["agent"],
            p["run_id"],
            listed(p["agent_cli_versions"]),
            f"{p['requested_model'] or 'default'} (reported: {listed(p['agent_models'])})",
            (
                f"{p['grader_model_requested'] or 'no grader'}"
                f" (reported: {listed(p['grader_models'])})"
            ),
            listed(p["grader_cli_versions"]),
            f"{p['trials_per_case']}{' + baseline' if p['baseline'] else ''}",
            commit,
        ]
        rows.append("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in cells) + "</tr>")
    head = [
        "iteration",
        "agent",
        "run",
        "agent CLI",
        "agent model",
        "grader model",
        "grader CLI",
        "trials per case",
        "commit",
    ]
    return _table(head, rows)


def _history(report: Mapping[str, Any], agent: str) -> str:
    flagged = {
        (r["scope"], r["metric"], r["to"]) for r in report["regressions"] if r["agent"] == agent
    }
    names = [c["name"] for c in report["columns"]]
    rows = []
    for row in report["history"][agent]:
        tds = "".join(
            _td(v, flag=(row["scope"], row["metric"], name) in flagged)
            for v, name in zip(row["values"], names, strict=True)
        )
        rows.append(f"<tr><th>{_e(row['scope'])}</th><td>{_e(row['metric'])}</td>{tds}</tr>")
    return _table(["scope", "metric", *names], rows)


def _section(report: Mapping[str, Any]) -> str:
    skill = _e(report["skill"])
    parts = [f'<section><h2 id="{skill}">{skill}</h2>']
    columns = ", ".join(
        f"{c['name']}{'' if c['recorded'] else ' (not recorded)'}" for c in report["columns"]
    )
    parts.append(f"<p>Iterations, oldest first: {_e(columns)}.</p>")
    if report["regressions"]:
        items = "".join(f"<li>{_e(describe(r))}</li>" for r in report["regressions"])
        parts.append(
            f'<h3>Regressions beyond {report["threshold"]:.2f}</h3><ul class="regressions">'
            f"{items}</ul>"
        )
    else:
        parts.append(f"<p>No regression beyond {report['threshold']:.2f}.</p>")
    parts.append(f"<h3>Agents by cases: {_e(report['matrix']['iteration'])}</h3>")
    parts.append(
        "<p>Trigger is trigger accuracy; pass rate is the outcome pass rate (outcome"
        " assertions and expectations together); Δ is the skill arm minus the baseline.</p>"
    )
    parts.append(_matrix(report))
    parts.append(f"<h3>Delta against the baseline: {_e(report['matrix']['iteration'])}</h3>")
    parts.append(_deltas_table(report))
    parts.append("<h3>Provenance</h3>")
    parts.append(_provenance(report))
    for comparison in report["comparisons"]:
        labels = ", ".join(comparison["labels"]) or "like-for-like"
        parts.append(
            f"<p>{_e(comparison['agent'])}: {_e(comparison['from'])} → {_e(comparison['to'])}:"
            f" {_e(labels)}.</p>"
        )
    for agent in report["agents"]:
        parts.append(f"<h3>History: {_e(agent)}</h3>")
        if not any(row["agent"] == agent for row in report["provenance"]):
            parts.append(f"<p>{_e(agent)} has not been run in any iteration.</p>")
            continue
        parts.append(_history(report, agent))
    parts.append("</section>")
    return "\n".join(parts)


STYLE = """
:root { color-scheme: light dark; --fg: #1b1b1b; --bg: #fdfdfc; --muted: #6b6b6b;
  --line: #d9d9d6; --bad: #b3261e; --bad-bg: #fbe9e7; }
@media (prefers-color-scheme: dark) {
  :root { --fg: #e8e8e6; --bg: #161616; --muted: #9a9a96; --line: #3a3a38;
    --bad: #f2b8b5; --bad-bg: #3b1d1b; }
}
body { font: 14px/1.45 system-ui, sans-serif; color: var(--fg); background: var(--bg);
  margin: 0 auto; max-width: 1200px; padding: 16px; }
table { border-collapse: collapse; margin: 8px 0 20px; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--line); padding: 4px 8px; text-align: left;
  white-space: nowrap; font-variant-numeric: tabular-nums; }
td.missing { color: var(--muted); font-style: italic; }
td.regressed, .regressions li { color: var(--bad); background: var(--bad-bg); }
"""


def render_html(reports: Sequence[Mapping[str, Any]]) -> str:
    """One offline page for the reports: inline CSS, no script, no external resource."""
    body = "\n".join(_section(r) for r in reports)
    legend = "; ".join(f"{STATES[key]}: {meaning}" for key, meaning in MEANINGS.items())
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Benchmark report</title><style>{STYLE}</style></head><body>"
        "<h1>Benchmark report</h1>"
        f"<p>Missing data is never a zero. {_e(legend)}.</p>\n{body}\n</body></html>\n"
    )
