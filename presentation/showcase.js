"use strict";

const cases = window.agentCityScenarios ?? [];
const number = new Intl.NumberFormat("en", {maximumFractionDigits: 1});
const score = new Intl.NumberFormat("en", {minimumFractionDigits: 2, maximumFractionDigits: 2});
const metrics = [
  ["congestion", "Congestion", "/100"],
  ["travelDelay", "Road delay", " min"],
  ["transitDelay", "Transit delay", " min"],
  ["emissions", "Emissions change", "%"],
  ["safetyRisk", "Safety risk", "/100"],
  ["energyLoad", "Energy load", "/100"],
];
const timeline = document.querySelector("#timeline");
const metricRows = document.querySelector("#metric-rows");
const status = document.querySelector("#forecast-status");

let activeCase = cases[0];
const formatPopulation = new Intl.NumberFormat("en");
const caseOptions = document.querySelector("#case-options");

function selectFrame(index) {
  const frame = activeCase.frames[index];
  [...timeline.children].forEach((button, position) => button.setAttribute("aria-pressed", position === index));
  status.textContent = `+${frame.minute} min · Incident phase ${frame.phase.toLowerCase()}`;
  metricRows.replaceChildren(...metrics.map(([key, label, unit]) => {
    const row = document.createElement("tr");
    if (key === activeCase.highlight) row.className = "focus-metric";
    const heading = document.createElement("th");
    heading.scope = "row";
    heading.textContent = label;
    row.append(heading);
    for (const value of [frame.baseline[key], frame.recommended[key]]) {
      const cell = row.insertCell();
      cell.textContent = number.format(value) + unit;
    }
    return row;
  }));
}

const images = {
  explanation: ["04-explanation.jpg", "Negotiation record from the university corridor scenario", "The application shows the combined campus measures and their revised score."],
  plan: ["07-execution-plan.jpg", "Execution plan from a later run of the university corridor scenario", "The execution plan shows completed steps, tool calls, delegations, and the awaiting operator review status."],
  audit: ["05-audit.jpg", "Audit trace from the university corridor scenario", "Logged events show the proposed revision, second simulation, and verification."],
  models: ["06-model-lab.jpg", "Model Lab capability controls", "The Model Lab supports streaming text, image analysis, embeddings, and city tools."],
};
const gallery = [...document.querySelectorAll("[data-evidence]")];
const evidenceImage = document.querySelector("#evidence-image");
const evidenceButton = document.querySelector("#evidence-image-button");
const evidenceCaption = document.querySelector("#evidence-caption");

function showEvidence(key) {
  const [file, caption, alt] = key === "comparison" && activeCase
    ? [activeCase.images.comparison, activeCase.label + " comparison at +30 minutes", "Captured strategy ranking beside baseline and recommended metrics."]
    : images[key] ?? ["03-comparison.jpg", "University corridor scenario comparison", "Captured strategy ranking and outcome comparison."];
  gallery.forEach(item => item.setAttribute("aria-pressed", item.dataset.evidence === key));
  evidenceImage.onerror = key === "plan" ? () => showEvidence("audit") : null;
  evidenceImage.src = "assets/screenshots/" + file;
  evidenceImage.alt = alt;
  evidenceButton.dataset.caption = caption;
  evidenceCaption.textContent = caption;
}
gallery.forEach(button => button.addEventListener("click", () => showEvidence(button.dataset.evidence)));

function selectCase(item) {
  activeCase = item;
  [...caseOptions.children].forEach(button => button.setAttribute("aria-pressed", button.dataset.case === item.id));
  const copy = {
    "case-name":item.label, "case-location":item.scenario.location, "case-brief":item.brief,
    "case-start":item.scenario.startsAt, "case-duration":item.scenario.duration+" min",
    "case-population":formatPopulation.format(item.population), "results-case":item.label,
    "strategy-name":item.name, "strategy-summary":item.summary,
    "baseline-score":score.format(item.scores.baseline), "recommended-score":score.format(item.scores.recommended),
  };
  for (const [id, value] of Object.entries(copy)) document.getElementById(id).textContent = value;
  const constraint = document.querySelector("#case-constraint");
  constraint.hidden = !item.restrictions;
  constraint.textContent = item.restrictions ? "Modeled constraint · " + item.restrictions : "";
  const screenshot = document.querySelector("#case-image");
  screenshot.src = "assets/screenshots/" + item.images.forecast;
  screenshot.alt = "Modeled forecast for " + item.label.toLowerCase() + " around " + item.scenario.location + ".";
  document.querySelector("#case-image-button").dataset.caption = item.label + " forecast at +30 minutes";
  timeline.replaceChildren(...item.frames.map((frame, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = frame.minute ? `+${frame.minute} min` : "Start";
    button.addEventListener("click", () => selectFrame(index));
    return button;
  }));
  selectFrame(item.frames.findIndex(frame => frame.minute === 30));
  showEvidence("comparison");
}

for (const item of cases) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.case = item.id;
  button.textContent = item.label;
  button.addEventListener("click", () => selectCase(item));
  caseOptions.append(button);
}
if (activeCase) selectCase(activeCase);
else status.textContent = "The recorded forecast is available in the deck.";

const viewer = document.querySelector("#viewer");
document.querySelectorAll("[data-viewer]").forEach(button => {
  button.addEventListener("click", () => {
    const source = button.querySelector("img");
    const target = document.querySelector("#viewer-image");
    target.src = source.src;
    target.alt = source.alt;
    document.querySelector("#viewer-caption").textContent = button.dataset.caption;
    viewer.showModal();
  });
});

const chapters = [...document.querySelectorAll(".chapter")];
const controls = document.querySelector("#stage-controls");
const counter = document.querySelector("#chapter-count");
const previous = document.querySelector("#previous");
const next = document.querySelector("#next");
const start = document.querySelector("#start-stage");
let current = -1;

function showChapter(index) {
  if (index < 0 || index >= chapters.length) return;
  current = index;
  chapters.forEach((chapter, position) => { chapter.hidden = position !== index; });
  counter.textContent = `${index + 1} / ${chapters.length}`;
  previous.disabled = index === 0;
  next.disabled = index === chapters.length - 1;
  const title = chapters[index].querySelector("h1,h2");
  title.tabIndex = -1;
  title.focus({preventScroll: true});
  window.scrollTo({top: 0, behavior: "instant"});
}

function exitPresentation() {
  current = -1;
  document.body.classList.remove("presenting");
  chapters.forEach(chapter => { chapter.hidden = false; });
  controls.hidden = true;
  if (document.fullscreenElement) void document.exitFullscreen().catch(() => {});
  start.focus();
}

start.addEventListener("click", () => {
  document.body.classList.add("presenting");
  controls.hidden = false;
  showChapter(0);
  if (document.documentElement.requestFullscreen) {
    void document.documentElement.requestFullscreen().catch(() => {});
  }
});
previous.addEventListener("click", () => showChapter(current - 1));
next.addEventListener("click", () => showChapter(current + 1));
document.querySelector("#leave-stage").addEventListener("click", exitPresentation);
document.addEventListener("fullscreenchange", () => {
  if (!document.fullscreenElement && current >= 0) exitPresentation();
});
document.addEventListener("keydown", event => {
  if (current < 0 || viewer.open || event.altKey || event.ctrlKey || event.metaKey) return;
  if (event.key === "Escape") exitPresentation();
  const direction = {ArrowRight: 1, PageDown: 1, ArrowLeft: -1, PageUp: -1}[event.key];
  if (direction) {
    event.preventDefault();
    showChapter(current + direction);
  }
});
document.querySelector('.hero a[href="#case"]').addEventListener("click", event => {
  if (current < 0) return;
  event.preventDefault();
  showChapter(1);
});
document.querySelector("#case-results-link").addEventListener("click", event => {
  if (current < 0) return;
  event.preventDefault();
  showChapter(2);
});
