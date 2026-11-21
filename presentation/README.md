# AgentCity Twin presentation

Open [the web showcase](index.html) directly in a browser. It works offline from this folder. Choose a scenario to load its recorded forecast, strategy scores, and five-point timeline. Select **Present** for a five-chapter view, use the arrow keys or Page Up and Page Down to navigate, and press Escape to exit. The evidence gallery opens screenshots at full size.

- [Presentation-maker prompt](presentation-maker-prompt.txt) explains the expected LaTeX outputs, screenshot placements, and design.
- [Audience PDF](agentcity-twin.pdf) and [editable Beamer source](agentcity-twin.tex) contain the eight-slide deck.
- [Speaker notes](speaker-notes.txt) include slide timings and a live-demo fallback. [Presenter PDF](agentcity-twin-presenter.pdf) pairs the deck with embedded notes.
- [Questions and answers](questions-and-answers.txt) covers the main technical and pilot questions.
- [Demo evidence](demo-evidence.json) holds the values, selected strategy, and provider details from the captured run. Original screenshots are under `assets/screenshots`.
- [Scenario evidence](scenario-evidence.json) contains the five recorded cases used by the web showcase. The audience deck follows the university accident.

Compile from this folder with a LaTeX installation that includes Beamer, `booktabs`, and `pgfpages`. Run each command twice to resolve slide counts.

```powershell
pdflatex -interaction=nonstopmode -halt-on-error agentcity-twin.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=agentcity-twin-presenter "\def\presenternotes{1}\input{agentcity-twin.tex}"
```

The web showcase uses plain HTML, CSS, and JavaScript with local fonts, data, and images. The main application remains available separately at `http://localhost:3100` when running.
