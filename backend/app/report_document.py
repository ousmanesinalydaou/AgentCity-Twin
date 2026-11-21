"""Versioned, print-ready reports generated from persisted run evidence."""

import json
from html import escape

from .config import ROOT

LOCALES = json.loads((ROOT / "data" / "report-locales.json").read_text(encoding="utf-8"))

TEMPLATES = {
    "decision": {"version": "1.0", "title": "Operator decision"},
    "research": {"version": "1.0", "title": "Research record"},
}
METRICS = {
    "congestion": "Congestion",
    "transitDelay": "Transit delay",
    "emissions": "Emissions change",
    "safetyRisk": "Safety risk",
    "energyLoad": "Energy load",
}


def visual(frame, bounds, label):
    min_x, min_y, max_x, max_y = bounds
    width, height = max(max_x - min_x, 0.00001), max(max_y - min_y, 0.00001)

    def project(latlon):
        return f"{12 + 276 * (latlon[0] - min_x) / width:.1f},{124 - 112 * (latlon[1] - min_y) / height:.1f}"

    paths = []
    for route in frame["flows"]:
        points = " ".join(map(project, route["coordinates"]))
        pressure = route["pressure"]
        color = "#164b39" if pressure < 44 else "#94610a" if pressure < 70 else "#a12c20"
        paths.append(f'<polyline points="{points}" stroke="{color}" stroke-width="3" fill="none"/>')
    return f'<svg viewBox="0 0 300 136" aria-label="{label}" role="img">' + "".join(paths) + "</svg>"


def render(run, template, minute, language="en"):
    words = LOCALES.get(language, {})

    def t(label):
        return escape(words.get(label, label))

    result = run["result"]
    option = TEMPLATES[template]
    before = next(frame for frame in result["baseline"]["timeline"] if frame["minute"] == minute)
    after = next(frame for frame in result["recommendation"]["timeline"] if frame["minute"] == minute)
    coords = [coord for item in before["flows"] for coord in item["coordinates"]]
    xs, ys = [point[0] for point in coords], [point[1] for point in coords]
    bounds = min(xs), min(ys), max(xs), max(ys)
    table = "".join(
        f"<tr><th>{t(label)}</th><td>{before['metrics'][metric]}</td><td>{after['metrics'][metric]}</td></tr>"
        for metric, label in METRICS.items()
    )
    strategies = "".join(
        f"<li>{escape(row['name'])} · {row['score']:.1f}/100</li>" for row in result["strategies"]
    )
    trace = "".join(f"<li>{escape(event['time'])} · {escape(event['text'])}</li>" for event in run["events"])
    leeway = "".join(f"<li>{escape(note)}</li>" for note in [*result["assumptions"], *result["limitations"]])
    references = "".join(
        f"<li>{escape(row['name'])} · {escape(row['summary'])} · {escape(row['evidence'])}</li>"
        for row in result["messages"]
    )
    report_key = template + "-" + option["version"]
    scenario = run["scenario"]
    uncertainty = "".join(
        f"<li>{t(METRICS[key])} · {value[0]} {t('to')} {value[1]}</li>"
        for key, value in after.get("intervals", {}).items()
        if key in METRICS
    )
    research = (
        (
            f"<h2>{t('Reproducibility')}</h2><p>{t('Seed')} {result['seed']} · {escape(result['model_version'])}</p>"
            f"<p>{t('Input hash')} <code>{escape(result['input_hash'])}</code></p>"
        )
        if template == "research"
        else ""
    )
    return f"""<!doctype html><html lang="{language}"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{escape(run["title"])} · AgentCity Twin</title>
<style>
body{{color:#142332;font:15px/1.5 system-ui;max-width:900px;margin:28px auto;padding:0 18px}}
h1,h2{{line-height:1.2}}small,figcaption{{color:#49647c}} .pair{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
figure{{margin:0;border:1px solid #cbd9df;padding:8px;border-radius:6px}}svg{{width:100%;display:block}}
table{{border-collapse:collapse;width:100%}}th,td{{padding:5px;text-align:left;border-bottom:1px solid #ddd}}
@media print{{body{{margin:0}} .pair,table{{break-inside:avoid}}}}
</style>
<header><small>AgentCity Twin · {t(option["title"])} · {report_key}</small><h1>{escape(run["title"])}</h1>
<p>{escape(scenario["location"])} · {escape(scenario["kind"])} · {t("Simulated")} · +{minute} min</p></header>
<h2>{escape(result["recommendation"]["name"])}</h2>
<p>{escape(result["recommendation"]["summary"])} · {result["confidence"]:.0%} {t("confidence")}</p>
<div class="pair"><figure>{visual(before, bounds, t("Modeled corridors"))}<figcaption>{t("Do nothing")}</figcaption></figure>
<figure>{visual(after, bounds, t("Modeled corridors"))}<figcaption>{t("Recommended")}</figcaption></figure></div>
<table><thead><tr><th>{t("Metric")}</th><th>{t("Do nothing")}</th><th>{t("Recommended")}</th></tr></thead><tbody>{table}</tbody></table>
<h2>{t("Strategy ranking")}</h2><ol>{strategies}</ol><h2>{t("Agent findings")}</h2><ul>{references}</ul>
<h2>{t("Assumptions and uncertainty")}</h2><ul>{leeway}{uncertainty}</ul>{research}<h2>{t("Audit trace")}</h2><ol>{trace}</ol></html>"""
