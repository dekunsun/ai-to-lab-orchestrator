/**
 * Builds the portfolio deck. Every figure here is read from the artifacts the
 * system itself produced, so the deck cannot drift from the code:
 *   artifacts/benchmark_results/cdte_benchmark*.json
 *   artifacts/triage_results/hydride_triage.json
 *   artifacts/evidence_results/evidence_loop.json
 *
 *   node docs/deck/build_deck.js
 */
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(__dirname, "ai_to_lab_orchestrator.pptx");
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), "utf8"));

const bench = read("artifacts/benchmark_results/cdte_benchmark.json");
const benchPerf = read("artifacts/benchmark_results/cdte_benchmark_cdte_performance_first.json");
const benchManu = read("artifacts/benchmark_results/cdte_benchmark_cdte_manufacturability_first.json");
const triage = read("artifacts/triage_results/hydride_triage.json");
const eloop = read("artifacts/evidence_results/evidence_loop.json");

// ---------------------------------------------------------------- palette
const INK = "18222B";      // graphite — dominant on dark slides
const STEEL = "1F5F8B";    // instrument blue — carried from the built UI
const SIGNAL = "C2410C";   // the system's own "hold" colour
const GROUND = "F1F4F7";   // cool off-white, never cream
const PASS = "15803D";
const MUTED = "5B6B78";
const LINE = "D4DCE3";
const WHITE = "FFFFFF";

const H = "Cambria";       // headers
const B = "Calibri";       // body
const M = "Courier New";   // rules, formulas, data

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5 — set BEFORE any slide
pres.author = "AI-to-Lab Orchestrator";
pres.title = "AI-to-Lab Orchestrator";

const L = 0.62;                          // left margin
const W = 13.33 - L * 2;                 // content width
// Derive track widths from W so a row of n cards always lands inside the margins.
const track = (n, gap) => (W - gap * (n - 1)) / n;

// ---------------------------------------------------------------- helpers
function chip(s, text, { x = L, y = 0.42, fill = STEEL, color = WHITE } = {}) {
  const w = Math.max(1.5, 0.15 * text.length + 0.42);
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h: 0.32, fill: { color: fill }, rectRadius: 0.16, line: { color: fill },
  });
  s.addText(text, {
    x, y, w, h: 0.32, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 10.5, bold: true, color, charSpacing: 1.2,
    align: "center", valign: "middle",
  });
}

function title(s, text, { y = 0.95, color = INK, size = 34, w = W } = {}) {
  s.addText(text, {
    x: L, y, w, h: 0.82, isTextBox: true, margin: 0,
    fontFace: H, fontSize: size, bold: true, color, valign: "middle",
  });
}

function kicker(s, text, { y = 1.74, color = MUTED, w = W, size = 14.5 } = {}) {
  s.addText(text, {
    x: L, y, w, h: 0.46, isTextBox: true, margin: 0,
    fontFace: B, fontSize: size, color, valign: "top", lineSpacing: 20,
  });
}

function card(s, { x, y, w, h, fill = WHITE, border = LINE }) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, fill: { color: fill }, rectRadius: 0.08,
    line: { color: border, width: 0.75 },
  });
}

function stat(s, { x, y, w, value, label, color = STEEL, size = 40 }) {
  s.addText(value, {
    x, y, w, h: 0.66, isTextBox: true, margin: 0,
    fontFace: H, fontSize: size, bold: true, color, valign: "middle",
  });
  s.addText(label, {
    x, y: y + 0.64, w, h: 0.5, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 11, color: MUTED, valign: "top", lineSpacing: 14,
  });
}

function body(s, text, o = {}) {
  s.addText(text, {
    x: o.x ?? L, y: o.y, w: o.w ?? W, h: o.h ?? 1.0, isTextBox: true, margin: 0,
    fontFace: B, fontSize: o.size ?? 13, color: o.color ?? INK,
    valign: "top", lineSpacing: o.lineSpacing ?? 19, align: o.align ?? "left",
  });
}

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: INK };
  return s;
}
function lightSlide() {
  const s = pres.addSlide();
  s.background = { color: GROUND };
  return s;
}

// ================================================================ 1. TITLE
{
  const s = darkSlide();
  chip(s, "PORTFOLIO  ·  AI FOR SCIENCE", { y: 1.5, fill: SIGNAL });
  s.addText("AI-to-Lab Orchestrator", {
    x: L, y: 2.0, w: W, h: 1.15, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 52, bold: true, color: WHITE, valign: "middle",
  });
  s.addText(
    "The operating layer between an AI's next-experiment suggestion\nand the evidence that it actually ran.",
    { x: L, y: 3.2, w: 9.2, h: 1.0, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 18, color: "AEBCC8", valign: "top", lineSpacing: 27 });

  const facts = [
    ["2", "use cases, both defensible"],
    ["65", "tests, including the governance and evidence layers"],
    ["30 x 30", "seed benchmark, reproducible from one script"],
  ];
  facts.forEach(([v, l], i) => {
    const x = L + i * 4.05;
    s.addText(v, { x, y: 4.75, w: 3.8, h: 0.55, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 30, bold: true, color: STEEL === INK ? WHITE : "6FA8CE", valign: "middle" });
    s.addText(l, { x, y: 5.3, w: 3.8, h: 0.5, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11.5, color: "8A9AA8", valign: "top" });
  });
  s.addText("A self-driving-lab orchestration prototype for materials discovery  ·  not a physics simulator",
    { x: L, y: 6.55, w: W, h: 0.35, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11, color: "6B7C8A", italic: true });
  s.addNotes("Opening frame: this is an operating-layer project, not a materials-modelling project. The claim I am making is about systems, data and governance judgment — and I say up front that it is not a physics simulator, because that boundary is the thing I want to be trusted on.");
}

// ================================================================ 2. PROBLEM
{
  const s = lightSlide();
  chip(s, "01  ·  THE PROBLEM");
  title(s, "Predictions outpace validation");
  kicker(s, "Models propose candidates far faster than labs can evaluate them. The bottleneck is not model\naccuracy — it is that a prediction does not automatically become an experiment, an experiment does not\nautomatically become trustworthy data, and trustworthy data does not automatically become a decision.",
    { y: 1.72 });

  const qs = [
    ["What should we try next?", "and by whose definition of a good result"],
    ["Is it safe to run?", "individually legal values can be jointly unsafe"],
    ["Did it actually run?", "or did it fail, and was the failure recorded"],
    ["Is the data good enough?", "not every completed run deserves to be believed"],
    ["What did we learn?", "which hypothesis did this settle, if any"],
  ];
  const y0 = 3.15, ch = 0.66, gap = 0.16;
  qs.forEach(([q, sub], i) => {
    const y = y0 + i * (ch + gap);
    card(s, { x: L, y, w: 6.2, h: ch });
    s.addShape(pres.ShapeType.roundRect, {
      x: L + 0.18, y: y + 0.19, w: 0.28, h: 0.28,
      fill: { color: SIGNAL }, rectRadius: 0.14, line: { color: SIGNAL } });
    s.addText(q, { x: L + 0.6, y: y + 0.04, w: 3.3, h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12.5, bold: true, color: INK, valign: "middle" });
    s.addText(sub, { x: L + 0.6, y: y + 0.32, w: 5.4, h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10.5, color: MUTED, valign: "middle" });
  });

  card(s, { x: 7.3, y: y0, w: 5.4, h: 4.0, fill: INK, border: INK });
  s.addText("Everything in that gap is operational.", {
    x: 7.62, y: y0 + 0.35, w: 4.8, h: 0.8, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 20, bold: true, color: WHITE, valign: "top", lineSpacing: 26 });
  s.addText(
    "Scheduling. Validation. Safety review. Provenance. Data quality. Deciding what is even eligible to feed back into a model.\n\nNone of it is a modelling problem. All of it decides how fast the loop actually turns — and the speed of that loop is the ceiling on how fast an AI-for-science programme can iterate.\n\nThat gap is what I built.",
    { x: 7.62, y: y0 + 1.25, w: 4.8, h: 2.5, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12.5, color: "C3D0DA", valign: "top", lineSpacing: 19 });
  s.addNotes("The point to land: I am not claiming to out-model a computational materials scientist. I am claiming the bottleneck sits in the operational layer, and that I understand it well enough to run programmes in it.");
}

// ================================================================ 3. SYSTEM
{
  const s = lightSlide();
  chip(s, "02  ·  THE SYSTEM");
  title(s, "Five layers, each answering one question");

  const layers = [
    ["Data contracts", "If a device changes its output shape, do we find out?", "Partial"],
    ["Orchestration", "How does an intent become an auditable sequence of steps?", "Done"],
    ["Experiment data", "What is the system's memory? Do failures count as data?", "Partial"],
    ["Decision", "What next, and by whose definition of “good”?", "Done"],
    ["Governance", "Who approved this, and which data may train a model?", "Done"],
  ];
  const y0 = 2.0, rh = 0.82, gap = 0.16;
  layers.forEach(([name, q, status], i) => {
    const y = y0 + i * (rh + gap);
    card(s, { x: L, y, w: W, h: rh });
    s.addText(name, { x: L + 0.3, y, w: 2.9, h: rh, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 15, bold: true, color: STEEL, valign: "middle" });
    s.addText(q, { x: L + 3.3, y, w: 7.0, h: rh, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12.5, color: INK, valign: "middle" });
    const done = status === "Done";
    s.addShape(pres.ShapeType.roundRect, {
      x: 11.0, y: y + 0.24, w: 1.0, h: 0.34,
      fill: { color: done ? "E6F2EA" : "FDF3E3" }, rectRadius: 0.17,
      line: { color: done ? "BEDCC9" : "EFD9AE" } });
    s.addText(status, { x: 11.0, y: y + 0.24, w: 1.0, h: 0.34, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10, bold: true, color: done ? PASS : "B45309",
      align: "center", valign: "middle" });
  });
  body(s, "Separated so each can be reasoned about — and swapped — on its own. The optimizer sits behind a two-method interface; the dashboard renders state and owns no workflow logic; orchestration and decisions run headless without importing Streamlit.",
    { y: 6.9, size: 11.5, color: MUTED, w: 12.0 });
  s.addNotes("If asked why five: because these are the five questions that have different owners in a real lab. Instruments, scheduling, data, science strategy, and safety are not one person's job.");
}

// ================================================================ 4. HONESTY
{
  const s = lightSlide();
  chip(s, "03  ·  DESIGN PRINCIPLE", { fill: SIGNAL });
  title(s, "Scientific honesty over fake physics");
  kicker(s, "Where physical fidelity matters, use published data. Where systems benchmarking matters, use a\ntransparent surrogate that is honest about being one. The two use cases were chosen to sit on\nopposite sides of that line.", { y: 1.72 });

  const cols = [
    { x: L, head: "CdTe thin-film process", tag: "TRANSPARENT SURROGATE", c: STEEL,
      is: ["A benchmark environment for orchestration and optimization",
           "Deliberately hard: observation noise, a narrow non-smooth treatment window, an over-treatment cliff, parameter interactions, outright failures",
           "Literature-inspired in qualitative behaviour only"],
      isnt: ["A physically accurate CdTe simulator", "Any claim about real device efficiency"] },
    { x: 7.0, head: "Hydride superconductors", tag: "PUBLISHED DATA", c: SIGNAL,
      is: ["22 candidates transcribed verbatim from Sanna et al., Communications Physics (2026)",
           "Triage, decision policy and validation planning built on top of published values",
           "Provenance enforced as a file boundary, with a test to hold it"],
      isnt: ["Any simulation of DFPT, electron-phonon coupling or Tc",
             "Any score the paper did not publish, presented as though it had"] },
  ];
  cols.forEach((c) => {
    card(s, { x: c.x, y: 3.1, w: 5.7, h: 3.65 });
    s.addShape(pres.ShapeType.roundRect, { x: c.x + 0.3, y: 3.35, w: 2.3, h: 0.3,
      fill: { color: c.c }, rectRadius: 0.15, line: { color: c.c } });
    s.addText(c.tag, { x: c.x + 0.3, y: 3.35, w: 2.3, h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 8.5, bold: true, color: WHITE, align: "center", valign: "middle", charSpacing: 1 });
    s.addText(c.head, { x: c.x + 0.3, y: 3.75, w: 5.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 17, bold: true, color: INK, valign: "middle" });
    s.addText(c.is.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < c.is.length - 1 } })), {
      x: c.x + 0.3, y: 4.25, w: 5.1, h: 1.45, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10.5, color: INK, valign: "top", paraSpaceAfter: 5, lineSpacing: 14 });
    s.addText("What it is not", { x: c.x + 0.3, y: 5.75, w: 5.1, h: 0.25, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10, bold: true, color: SIGNAL, charSpacing: 0.6 });
    s.addText(c.isnt.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < c.isnt.length - 1 } })), {
      x: c.x + 0.3, y: 6.02, w: 5.1, h: 0.62, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10.5, color: MUTED, valign: "top", paraSpaceAfter: 3, lineSpacing: 14 });
  });
  s.addNotes("This is the slide I would lead with if I only had one. Knowing where it is legitimate to simulate and where it is not is the judgment the role actually needs.");
}

// ================================================================ 5. LOOP
{
  const s = lightSlide();
  chip(s, "04  ·  USE CASE 1");
  title(s, "The closed loop, and what it refuses to do");

  const steps = [
    ["Propose", "optimizer suggests\nthe next parameters"],
    ["Review", "bounds, then hazard\nrules on combinations"],
    ["Execute", "six virtual instruments,\nin YAML order"],
    ["Score", "measurements become\none number, via policy"],
    ["Gate", "only clean, successful\nruns feed back"],
  ];
  const bgap = 0.31, bw = track(5, bgap), y0 = 2.1;
  steps.forEach(([h2, d], i) => {
    const x = L + i * (bw + bgap);
    card(s, { x, y: y0, w: bw, h: 1.72 });
    s.addText(String(i + 1), { x: x + 0.22, y: y0 + 0.16, w: 0.4, h: 0.3, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 15, bold: true, color: SIGNAL, valign: "middle" });
    s.addText(h2, { x: x + 0.62, y: y0 + 0.16, w: 1.5, h: 0.3, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 15, bold: true, color: INK, valign: "middle" });
    s.addText(d, { x: x + 0.22, y: y0 + 0.62, w: bw - 0.44, h: 0.95, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10.5, color: MUTED, valign: "top", lineSpacing: 14 });
    if (i < steps.length - 1) {
      s.addText("→", { x: x + bw + 0.02, y: y0 + 0.6, w: 0.27, h: 0.4, isTextBox: true, margin: 0,
        fontFace: B, fontSize: 15, color: LINE, align: "center", valign: "middle" });
    }
  });

  card(s, { x: L, y: 4.2, w: 6.2, h: 2.45, fill: "FDEEE6", border: "F0C4AE" });
  s.addText("blocked  ≠  failed", { x: L + 0.32, y: 4.45, w: 5.6, h: 0.42, isTextBox: true, margin: 0,
    fontFace: M, fontSize: 19, bold: true, color: SIGNAL, valign: "middle" });
  body(s, "A failure means a sample was consumed and produced nothing. A block means the gate refused to consume one at all. They cost a real lab completely different amounts, so they are separate statuses and the benchmark reports them separately.\n\nA blocked experiment runs zero devices.",
    { x: L + 0.32, y: 4.95, w: 5.6, h: 1.6, size: 11.5, lineSpacing: 16 });

  card(s, { x: 7.1, y: 4.2, w: 5.6, h: 2.45 });
  s.addText("The guardrail is set inside the uncertainty band", {
    x: 7.42, y: 4.42, w: 5.0, h: 0.5, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 15, bold: true, color: INK, valign: "middle", lineSpacing: 19 });
  s.addText("blocks at  440 °C / 40 min\ndegrades at  450 °C / 45 min", {
    x: 7.42, y: 4.98, w: 5.0, h: 0.62, isTextBox: true, margin: 0,
    fontFace: M, fontSize: 12.5, color: STEEL, valign: "top", lineSpacing: 17 });
  body(s, "A real lab does not know exactly where the cliff is, so the rule fires before the sample is destroyed. This costs reachable search space — which is why blocked is reported as its own rate. Governance is not free, and the system shows its price.",
    { x: 7.42, y: 5.72, w: 5.0, h: 0.85, size: 11, color: MUTED, lineSpacing: 15 });
  s.addNotes("The distinction between blocked and failed is the single detail that most reliably shows I have thought about lab economics rather than just about code.");
}

// ================================================================ 6. BENCHMARK
{
  const s = lightSlide();
  chip(s, "05  ·  DOES IT ACTUALLY WORK");
  title(s, "Bayesian optimization vs random, 30 seeds");

  const bo = bench.results.bayesian_optimization;
  const rs = bench.results.random_search;
  const n = bench.budget;
  const labels = Array.from({ length: n }, (_, i) =>
    (i + 1) === 1 || (i + 1) % 5 === 0 ? String(i + 1) : "");

  s.addChart(pres.ChartType.line,
    [
      { name: "Bayesian optimization", labels, values: bo.curve_median },
      { name: "Random search", labels, values: rs.curve_median },
      { name: "Noise-free ceiling", labels, values: labels.map(() => bench.surrogate_ceiling) },
    ],
    { x: L, y: 1.95, w: 8.05, h: 4.35,
      chartColors: [STEEL, "9AA7B2", "CDD6DE"],
      lineSize: 3, lineDataSymbol: "none",
      showLegend: true, legendPos: "b", legendFontFace: B, legendFontSize: 10.5, legendColor: MUTED,
      showTitle: false,
      valAxisMinVal: 0.2, valAxisMaxVal: 0.95,
      valAxisLabelFontFace: B, valAxisLabelFontSize: 10, valAxisLabelColor: MUTED,
      catAxisLabelFontFace: B, catAxisLabelFontSize: 10, catAxisLabelColor: MUTED,
      valGridLine: { color: "E2E8ED", size: 1 },
      catGridLine: { style: "none" },
      valAxisLineShow: false, catAxisLineShow: true, catAxisLineColor: LINE,
      valAxisTitle: "Best objective found so far", showValAxisTitle: true,
      valAxisTitleFontFace: B, valAxisTitleFontSize: 10.5, valAxisTitleColor: MUTED,
      catAxisTitle: "Experiments run (fixed budget of 30)", showCatAxisTitle: true,
      catAxisTitleFontFace: B, catAxisTitleFontSize: 10.5, catAxisTitleColor: MUTED,
    });

  const sx = 9.1;
  stat(s, { x: sx, y: 2.0, w: 3.6, value: bo.final_best.median.toFixed(3),
    label: "Bayesian optimization, median best\nIQR [" + bo.final_best.q1.toFixed(3) + ", " + bo.final_best.q3.toFixed(3) + "]" });
  stat(s, { x: sx, y: 3.35, w: 3.6, value: rs.final_best.median.toFixed(3), color: "7A8894",
    label: "Random search, median best\nIQR [" + rs.final_best.q1.toFixed(3) + ", " + rs.final_best.q3.toFixed(3) + "]" });
  stat(s, { x: sx, y: 4.7, w: 3.6, value: bench.paired.a_wins + " / " + bench.paired.n, color: SIGNAL,
    label: "seeds where BO won, median gap +" + bench.paired.median_gap.toFixed(3) +
           "\nPaired comparison is valid because both\nmethods meet the same lab noise." });

  body(s, "Every figure on this slide is produced by scripts/run_cdte_benchmark.py and written to artifacts/. Nothing is hand-entered — the deck reads the same JSON the dashboard does.",
    { y: 6.72, size: 11, color: MUTED, w: 12.0 });
  s.addNotes("If asked how I know BO is better: fixed budget, 30 seeds, median and IQR rather than a single trajectory, and common random numbers so the per-seed comparison is actually paired.");
}

// ================================================================ 7. HONEST READING
{
  const s = lightSlide();
  chip(s, "06  ·  READING IT HONESTLY", { fill: SIGNAL });
  title(s, "Three things I say before I am asked");

  const items = [
    ["The bands overlap", "BO wins in the median and on two seeds in three, but it does not dominate. On a five-dimensional landscape with a 30-experiment budget, clean separation would be evidence the benchmark was too easy — not evidence the optimizer is good."],
    ["BO is behind early", "It runs an initial design first, so it trails random search for roughly the first ten experiments. The advantage is sample efficiency later in the budget, not from experiment one. A chart cropped at 10 would tell the opposite story."],
    ["Runs exceed the ceiling", "The dashed line is the noise-free maximum, but the reported score is a noisy observation — so best-found is an optimistically biased estimator. Taking a max over noisy draws captures luck. Any lab ranking candidates on a single best-observed inherits this, which is why replication is a governance concern."],
  ];
  const cgap = 0.3, cw = track(3, cgap);
  items.forEach(([h2, d], i) => {
    const x = L + i * (cw + cgap);
    card(s, { x, y: 2.1, w: cw, h: 3.5 });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.3, y: 2.38, w: 0.34, h: 0.34,
      fill: { color: SIGNAL }, rectRadius: 0.17, line: { color: SIGNAL } });
    s.addText(String(i + 1), { x: x + 0.3, y: 2.38, w: 0.34, h: 0.34, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, bold: true, color: WHITE, align: "center", valign: "middle" });
    s.addText(h2, { x: x + 0.3, y: 2.85, w: cw - 0.6, h: 0.44, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 16, bold: true, color: INK, valign: "middle" });
    s.addText(d, { x: x + 0.3, y: 3.35, w: cw - 0.6, h: 2.2, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11, color: MUTED, valign: "top", lineSpacing: 15.5 });
  });

  card(s, { x: L, y: 5.85, w: W, h: 1.0, fill: INK, border: INK });
  s.addText("A portfolio that only shows what worked is asking to be caught. Putting the weaknesses in the product surface itself — they are printed in the dashboard and the README — is cheaper than being asked.",
    { x: L + 0.4, y: 5.85, w: W - 0.8, h: 1.0, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, color: "C3D0DA", italic: true, valign: "middle" });
  s.addNotes("These three caveats are printed in the dashboard UI and the README, not just in this deck. That is the point — the honesty is in the product, not in the pitch.");
}

// ================================================================ 8. POLICIES
{
  const s = lightSlide();
  chip(s, "07  ·  DECISION TRANSPARENCY");
  title(s, "The weights are a policy, not a constant");
  kicker(s, "How much is phase purity worth relative to efficiency? That is a research-strategy question, not a\nproperty of an XRD machine. So the weights live in versioned policy files, every experiment records\nwhich policy scored it, and the same mechanism drives hydride triage.", { y: 1.72 });

  const pick = (p) => p.results.bayesian_optimization;
  const rows = [
    ["Performance first", pick(benchPerf)],
    ["Balanced device quality", pick(bench)],
    ["Manufacturability first", pick(benchManu)],
  ];
  const head = ["Policy", "Median best", "Treatment time", "Treatment temp", "Dopant"];
  const colX = [L, 4.7, 6.7, 8.9, 11.1];
  const colW = [4.0, 1.9, 2.1, 2.1, 1.6];

  head.forEach((h2, i) => s.addText(h2, {
    x: colX[i], y: 3.2, w: colW[i], h: 0.34, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 10.5, bold: true, color: MUTED, charSpacing: 0.8, valign: "middle" }));

  rows.forEach(([name, r], i) => {
    const y = 3.62 + i * 0.72;
    const hero = name.startsWith("Manufactur");
    card(s, { x: L - 0.14, y, w: W + 0.28, h: 0.62,
      fill: hero ? "E9F0F6" : WHITE, border: hero ? "BCD3E5" : LINE });
    const p = r.median_best_params;
    const cells = [name, r.final_best.median.toFixed(3),
      p.cdcl2_treatment_time_min.toFixed(1) + " min",
      p.cdcl2_treatment_temp_c.toFixed(1) + " °C",
      p.dopant_pct.toFixed(1) + " %"];
    cells.forEach((c, j) => s.addText(c, {
      x: colX[j], y, w: colW[j], h: 0.62, isTextBox: true, margin: 0,
      fontFace: j === 0 ? B : M, fontSize: j === 0 ? 13 : 12.5,
      bold: j === 0, color: j === 0 ? INK : (hero ? STEEL : MUTED), valign: "middle" }));
  });

  card(s, { x: L, y: 5.95, w: W, h: 1.0, fill: "FDEEE6", border: "F0C4AE" });
  s.addText([
    { text: "Median best is not comparable across these rows. ", options: { bold: true, color: SIGNAL } },
    { text: "Each policy defines a different objective, so a higher number does not mean a better process. The comparable quantity is the operating point: manufacturability-first converges on a treatment twelve minutes shorter and lighter doping — a visibly more conservative process. Treatment temperature lands near 388 °C under every policy, because that window dominates the landscape. Policy influences the parameters the objective leaves room to argue about.",
      options: { color: INK } },
  ], { x: L + 0.35, y: 5.95, w: W - 0.7, h: 1.0, isTextBox: true, margin: 0,
       fontFace: B, fontSize: 11.5, valign: "middle", lineSpacing: 15.5 });
  s.addNotes("Stating that the scores are not comparable across rows is the whole slide. A candidate who shows this table without that caveat has shown a bug, not a feature.");
}

// ================================================================ 9. HYDRIDE
{
  const s = lightSlide();
  chip(s, "08  ·  USE CASE 2");
  title(s, "Published data, and judgment kept visible");
  kicker(s, "The paper publishes λ, ω_log and an Allen–Dynes Tc. It publishes no score, no confidence and no\nfeasibility. Ranking needs those — so they are computed from documented rules and kept in\nseparate files. Provenance is a file boundary, not a convention, and a test fails if it erodes.", { y: 1.72 });

  const tiers = [
    ["PUBLISHED", "datasets/hydrides/", STEEL,
     "Transcribed verbatim from Tables 1–2.\nλ = 1.00 · ω_log = 341.59 K · Tc = 23.5 K"],
    ["DERIVED", "triage/derive.py", "4A86AD",
     "A documented transform of published values.\nTc confidence, from coupling regime and\nwhether a refinement exists."],
    ["ANALYST", "configs/triage/", SIGNAL,
     "Judgment encoded as a versioned rule set.\nSynthesis feasibility, from elemental\nconstraints. Labelled as judgment."],
  ];
  const cgap = 0.3, cw = track(3, cgap);
  tiers.forEach(([tag, where, col, d], i) => {
    const x = L + i * (cw + cgap);
    card(s, { x, y: 3.15, w: cw, h: 2.0 });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.3, y: 3.42, w: 1.5, h: 0.3,
      fill: { color: col }, rectRadius: 0.15, line: { color: col } });
    s.addText(tag, { x: x + 0.3, y: 3.42, w: 1.5, h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 9, bold: true, color: WHITE, align: "center", valign: "middle", charSpacing: 1 });
    s.addText(where, { x: x + 1.92, y: 3.42, w: cw - 2.2, h: 0.3, isTextBox: true, margin: 0,
      fontFace: M, fontSize: 10, color: MUTED, valign: "middle" });
    s.addText(d, { x: x + 0.3, y: 3.85, w: cw - 0.6, h: 1.1, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11, color: INK, valign: "top", lineSpacing: 15 });
  });

  card(s, { x: L, y: 5.4, w: W, h: 1.5, fill: INK, border: INK });
  s.addText("Only 1 of 22 candidates has a beyond-Allen–Dynes Tc.", {
    x: L + 0.4, y: 5.62, w: W - 0.8, h: 0.38, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 17, bold: true, color: WHITE, valign: "middle" });
  s.addText("For that one, refinement moved 23.5 K → 17 K, which the authors call “an uncommon deviation”. Every other ranking rests on a number the paper's own authors caution against over-reading — so confidence is weighted separately from Tc, rather than folded invisibly into it.",
    { x: L + 0.4, y: 6.05, w: W - 0.8, h: 0.7, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: "C3D0DA", valign: "top", lineSpacing: 16 });
  s.addNotes("Source: Sanna, Cerqueira, Cubuk, Errea and Fang, Communications Physics 2026. I transcribed from the preprint; the refined Tc is reported four different ways in the paper and SOURCE.md records that ambiguity rather than hiding it.");
}

// ================================================================ 10. FINDING
{
  const s = lightSlide();
  chip(s, "09  ·  WHAT THE TRIAGE SURFACED", { fill: SIGNAL });
  title(s, "The finding a Tc-ordered list cannot show");

  card(s, { x: L, y: 2.05, w: 6.0, h: 2.5, fill: "FDEEE6", border: "F0C4AE" });
  s.addText("10 of 22", { x: L + 0.35, y: 2.3, w: 2.4, h: 0.62, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 40, bold: true, color: SIGNAL, valign: "middle" });
  s.addText("candidates contain technetium", { x: L + 0.35, y: 2.92, w: 5.3, h: 0.3, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 13, bold: true, color: INK, valign: "middle" });
  body(s, "It has no stable isotope and needs a licensed facility. That constraint is visible from the formula alone and invisible in any ranking sorted by predicted Tc. Feasibility combines as a minimum, not a mean — one disqualifying element is not offset by three convenient ones.",
    { x: L + 0.35, y: 3.26, w: 5.3, h: 0.85, size: 11, lineSpacing: 15 });

  card(s, { x: 6.95, y: 2.05, w: 5.76, h: 2.5 });
  s.addText("Ranks move with the policy", { x: 7.3, y: 2.25, w: 5.1, h: 0.34, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 15, bold: true, color: INK, valign: "middle" });
  const sens = triage.sensitivity;
  const find = (f) => sens.find((r) => r.formula === f);
  const shown = ["LiZrH6Ru", "Ta6MoH16", "EuCdH6Ru", "EuLuTcH6"].map(find).filter(Boolean);
  const hx = [7.3, 9.5, 10.5, 11.5];
  ["Candidate", "Bal.", "High-Tc", "Feas."].forEach((h2, i) =>
    s.addText(h2, { x: hx[i], y: 2.64, w: i === 0 ? 2.1 : 0.95, h: 0.26, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 9.5, bold: true, color: MUTED, valign: "middle",
      align: i === 0 ? "left" : "center" }));
  shown.forEach((r, i) => {
    const y = 2.94 + i * 0.3;
    const swing = r.rank_spread >= 7;
    const vals = [r.ranks.hydride_balanced_validation, r.ranks.hydride_high_tc_seeking,
                  r.ranks.hydride_lab_feasible_first];
    s.addText(r.formula, { x: hx[0], y, w: 2.1, h: 0.28, isTextBox: true, margin: 0,
      fontFace: M, fontSize: 11, color: INK, valign: "middle" });
    vals.forEach((v, j) => s.addText(String(v), {
      x: hx[j + 1], y, w: 0.95, h: 0.28, isTextBox: true, margin: 0,
      fontFace: M, fontSize: 11, bold: swing, color: swing ? SIGNAL : MUTED,
      align: "center", valign: "middle" }));
  });
  s.addText("EuCdH6Ru moves 2 → 9 between policies — the warning label on every other row.",
    { x: 7.3, y: 4.2, w: 5.1, h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10.5, color: MUTED, italic: true, valign: "middle" });

  card(s, { x: L, y: 4.78, w: W, h: 1.45, fill: "E6F2EA", border: "BEDCC9" });
  s.addText("The consensus shortlist is the useful output, not rank 1.", {
    x: L + 0.4, y: 4.98, w: W - 0.8, h: 0.36, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 17, bold: true, color: PASS, valign: "middle" });
  s.addText(triage.consensus_shortlist.join("  ·  ") +
    "  —  these sit in the top five under every policy considered. They are what a lab validates regardless of whose priorities win the argument, which is the question a programme lead actually has to answer.",
    { x: L + 0.4, y: 5.38, w: W - 0.8, h: 0.7, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: INK, valign: "top", lineSpacing: 16 });

  body(s, "A single ranking presented as the answer would manufacture authority the data does not carry. The sensitivity view and the consensus shortlist are the honest output.",
    { y: 6.45, size: 11.5, color: MUTED });
  s.addNotes("The technetium finding is the one to lead with in conversation: it is checkable, it is chemistry rather than modelling, and it reframes the whole cohort.");
}

// ================================================================ 11. JOIN
{
  const s = lightSlide();
  chip(s, "10  ·  ARCHITECTURE PAYOFF");
  title(s, "One system, not two demos in one repository");
  kicker(s, "Triage does not end at a ranked table. The selected candidate becomes a workflow that enters the\nsame machinery a CdTe experiment does — same parser, same safety gate, no orchestrator changes.", { y: 1.72 });

  const flow = ["Ranked shortlist", "Validation plan\n(generated YAML)", "workflow_parser\n(unchanged)",
                "safety_gate\n(unchanged)", "Hypothesis\nregistered"];
  const bgap = 0.31, bw = track(5, bgap), y0 = 2.95;
  flow.forEach((t, i) => {
    const x = L + i * (bw + bgap);
    const reused = i === 2 || i === 3;
    card(s, { x, y: y0, w: bw, h: 1.15, fill: reused ? "E9F0F6" : WHITE,
      border: reused ? "BCD3E5" : LINE });
    s.addText(t, { x: x + 0.18, y: y0, w: bw - 0.36, h: 1.15, isTextBox: true, margin: 0,
      fontFace: reused ? M : B, fontSize: reused ? 11.5 : 12.5, bold: !reused,
      color: reused ? STEEL : INK, align: "center", valign: "middle", lineSpacing: 15 });
    if (i < flow.length - 1) s.addText("→", {
      x: x + bw + 0.02, y: y0 + 0.37, w: 0.27, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 15, color: LINE, align: "center", valign: "middle" });
  });

  card(s, { x: L, y: 4.5, w: W, h: 1.75, fill: INK, border: INK });
  s.addText("The CdTe safety gate blocked a hydride hazard it had never seen.", {
    x: L + 0.4, y: 4.72, w: W - 0.8, h: 0.38, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 18, bold: true, color: WHITE, valign: "middle" });
  s.addText("750 °C  with  150 bar H₂   →   blocked: hydrogen_pressure_at_temperature", {
    x: L + 0.4, y: 5.15, w: W - 0.8, h: 0.32, isTextBox: true, margin: 0,
    fontFace: M, fontSize: 13, color: "F0A07A", valign: "middle" });
  s.addText("Both values are individually within bounds. The generated workflow declares its own hazard rules and the existing gate enforces them correctly on first sight. A test asserts this — if it ever fails, the project has gone back to being two demos in one repository.",
    { x: L + 0.4, y: 5.52, w: W - 0.8, h: 0.65, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: "C3D0DA", valign: "top", lineSpacing: 16 });

  body(s, "Plans stop at awaiting_device_implementation — no hydride synthesis is simulated, because there is no honest way to. That is the forward path. What comes back across the same seam is the next slide.",
    { y: 6.45, size: 11.5, color: MUTED });
  s.addNotes("If someone asks what the hardest architectural decision was: making triage an entry point into the existing loop rather than a parallel module. It is the difference between a system and a portfolio of scripts.");
}

// ================================================================ 12. EVIDENCE LOOP
{
  const s = lightSlide();
  chip(s, "11  ·  CLOSING THE LOOP", { fill: SIGNAL });
  title(s, "A measurement changes the ranking that proposed it");
  kicker(s, "Evidence is received, never manufactured. There are no hydride devices, so records enter from\noutside — an instrument, a collaborator, a paper. A record with no named recorder or stated source\nis rejected at load: a measurement nobody will sign for cannot overturn a prediction.", { y: 1.72 });

  const cal = eloop.calibration;
  const inc = eloop.records.find((r) => r.verdict === "inconclusive");
  // the module's identifier is right for logs and data; a slide wants the name
  const calText = cal.description.replace(/allen_dynes/g, "Allen\u2013Dynes");

  // --- the two judgments that do the work ---
  card(s, { x: L, y: 3.15, w: 6.0, h: 1.62, fill: "FDEEE6", border: "F0C4AE" });
  s.addText("A null result is meaningless without its floor", {
    x: L + 0.32, y: 3.34, w: 5.4, h: 0.32, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 15, bold: true, color: SIGNAL, valign: "middle" });
  s.addText(inc
    ? `${inc.formula}: no transition seen — but the rig reached only ${inc.measurement_floor_k} K and the prediction is ${inc.predicted_tc_k} K. The run could not have observed what it was testing, so it refutes nothing. Marked inconclusive, excluded from the calibration, and its hypothesis stays open.`
    : "An experiment that could not have seen the effect is not evidence the effect is absent.",
    { x: L + 0.32, y: 3.7, w: 5.4, h: 0.95, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10.5, color: INK, valign: "top", lineSpacing: 14.5 });

  card(s, { x: L, y: 4.92, w: 6.0, h: 1.48 });
  s.addText("Evidence about one compound calibrates the method", {
    x: L + 0.32, y: 5.11, w: 5.4, h: 0.32, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 15, bold: true, color: STEEL, valign: "middle" });
  s.addText(`21 of 22 candidates rest on Allen–Dynes alone. ${calText} A calibration lowers confidence and never rewrites a prediction — a "corrected" Tc would invent a number nobody computed.`,
    { x: L + 0.32, y: 5.47, w: 5.4, h: 0.82, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10.5, color: INK, valign: "top", lineSpacing: 14.5 });

  // --- the cohort, before and after ---
  card(s, { x: 7.1, y: 3.15, w: 5.6, h: 3.25 });
  s.addText("The cohort re-ranks", { x: 7.42, y: 3.36, w: 5.0, h: 0.32, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 15, bold: true, color: INK, valign: "middle" });

  const hx = [7.42, 9.58, 10.42, 11.3];
  const hw = [2.1, 0.8, 0.8, 1.4];
  ["Candidate", "was", "now", "Tc source"].forEach((h2, i) =>
    s.addText(h2, { x: hx[i], y: 3.76, w: hw[i], h: 0.26, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 9.5, bold: true, color: MUTED, valign: "middle",
      align: i === 0 || i === 3 ? "left" : "center" }));

  eloop.ranking_after.slice(0, 6).forEach((r, i) => {
    const y = 4.06 + i * 0.33;
    const moved = r.move !== 0;
    const col = moved ? (r.move > 0 ? PASS : SIGNAL) : MUTED;
    s.addText(r.formula, { x: hx[0], y, w: hw[0], h: 0.3, isTextBox: true, margin: 0,
      fontFace: M, fontSize: 10.5, color: INK, valign: "middle" });
    s.addText(String(r.was), { x: hx[1], y, w: hw[1], h: 0.3, isTextBox: true, margin: 0,
      fontFace: M, fontSize: 10.5, color: MUTED, align: "center", valign: "middle" });
    s.addText(String(r.rank) + (moved ? ` (${r.move > 0 ? "+" : ""}${r.move})` : ""), {
      x: hx[2], y, w: hw[2], h: 0.3, isTextBox: true, margin: 0,
      fontFace: M, fontSize: 10.5, bold: moved, color: col, align: "center", valign: "middle" });
    s.addText(r.tc_source === "allen_dynes" ? "Allen–Dynes" : r.tc_source, {
      x: hx[3], y, w: hw[3], h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10, bold: r.tc_source === "measured",
      color: r.tc_source === "measured" ? STEEL : MUTED, valign: "middle" });
  });
  s.addText("A measured Tc supersedes every calculation, and the hypothesis moves from proposed to supported or contradicted.",
    { x: 7.42, y: 6.04, w: 5.0, h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10, color: MUTED, italic: true, valign: "top", lineSpacing: 13 });

  // --- the behaviour I did not design and only saw by running it ---
  card(s, { x: L, y: 6.56, w: W, h: 0.76, fill: INK, border: INK });
  s.addText([
    { text: "Measuring the leader low moved candidates nobody tested. ",
      options: { bold: true, color: WHITE } },
    { text: "Tc is normalized against the best in the cohort, so when the leader falls every untested compound becomes relatively more attractive — partly offset by the confidence penalty the same evidence applied to the method. A ranking is a statement about a set, not about a compound.",
      options: { color: "C3D0DA" } },
  ], { x: L + 0.4, y: 6.56, w: W - 0.8, h: 0.76, isTextBox: true, margin: 0,
       fontFace: B, fontSize: 10.5, valign: "middle", lineSpacing: 14 });

  s.addNotes("Worth dwelling on in conversation: I did not design the second-order effect, I saw it by running the loop. It is the clearest evidence that this is a system with behaviour rather than a set of scripts.");
}

// ================================================================ 12. BENCH REVIEW
{
  const s = lightSlide();
  chip(s, "12  ·  THE OPERATOR SURFACE");
  title(s, "Where a person actually meets the loop");

  s.addImage({ path: path.join(ROOT, "docs/mockups/bench_review_shot.png"),
    x: L, y: 1.95, w: 7.4, h: 4.85, sizing: { type: "crop", w: 7.4, h: 4.85 } });

  const notes = [
    ["The approval queue is the hero", "The held experiment is the only thing on the loop that needs a human. Everything else — proposing, executing, logging — does not. Putting approval anywhere but first would mean missing why this screen exists."],
    ["Every value is real output", "The held parameters, the triggered rule, the measurements, the objective breakdown and both artefacts are genuine system output, not illustration."],
    ["Sized for gloved hands", "60px touch targets, no text entry, high contrast. A tablet at the bench, not a dashboard at a desk."],
  ];
  let y = 2.0;
  notes.forEach(([h2, d]) => {
    s.addShape(pres.ShapeType.roundRect, { x: 8.3, y: y + 0.04, w: 0.26, h: 0.26,
      fill: { color: SIGNAL }, rectRadius: 0.13, line: { color: SIGNAL } });
    s.addText(h2, { x: 8.72, y, w: 4.0, h: 0.34, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 14, bold: true, color: INK, valign: "middle" });
    s.addText(d, { x: 8.72, y: y + 0.38, w: 4.0, h: 1.1, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11, color: MUTED, valign: "top", lineSpacing: 15 });
    y += 1.62;
  });
  body(s, "A high-fidelity prototype is a product manager's deliverable. Building it in React would have demonstrated wanting to be a front-end engineer instead.",
    { x: 8.72, y: 6.5, w: 4.0, size: 10.5, color: MUTED, lineSpacing: 14 });
  s.addNotes("Prompted by watching how an automated-lab company actually runs their floor: an operator with gloves on, working from a tablet at the bench. That fixed the form factor.");
}

// ================================================================ 13. DEFECTS
{
  const s = darkSlide();
  chip(s, "13  ·  WHAT WENT WRONG", { fill: SIGNAL });
  title(s, "Six defects I found in my own build", { color: WHITE });
  kicker(s, "These are real, not hypotheticals, and they are documented in the repository. Five of the six were silent \u2014 the system looked correct while being wrong.",
    { y: 1.68, color: "8A9AA8" });

  const defects = [
    ["The safety gate protected nothing", "Its hazard region was a strict subset of the true failure region, so every experiment it flagged was already doomed. It prevented zero damage while appearing to work in every demo.", "Governance fails identically to how it succeeds. It needs a test, not a demo."],
    ["The benchmark numbers were wrong", "The README claimed a BO median of 0.84. The measured value was 0.806, and no script in the repository produced either number.", "One script is now the sole source of every published figure."],
    ["One RNG served lab and optimizer", "BO draws ~512 candidates per iteration, random search draws 5 \u2014 so the two methods faced different measurement noise. The per-seed comparison was meaningless.", "Separate streams, and common random numbers across methods."],
    ["BO got trapped in failure regions", "Failed experiments yield no objective, so a naive surrogate never learns to avoid them and keeps re-proposing into the dead zone, burning budget.", "A feasibility penalty and an escape hatch \u2014 a real constrained-BO problem."],
    ["Rounding moved the median by 0.006", "Rounding each weighted term to six decimals \u2014 a 1e-4 perturbation \u2014 changed which point the GP held as incumbent, changed the argmax of Expected Improvement, and redirected the whole search.", "Closed loops are chaotically sensitive to their own numerics. Round for display, never before a decision."],
    ["Fabricated data labelled as published", "An earlier version shipped a 25-row hydride dataset whose header said the values came straight from the paper. Three compounds in it appear nowhere in that paper. Invented numbers, presented as measurements.", "A fabricated row is indistinguishable from a transcribed one once they share a file. Provenance has to be a boundary, not a comment."],
  ];
  let y = 2.36;
  defects.forEach(([h2, what, taught], i) => {
    s.addText(String(i + 1).padStart(2, "0"), { x: L, y, w: 0.5, h: 0.3, isTextBox: true, margin: 0,
      fontFace: M, fontSize: 11.5, bold: true, color: SIGNAL, valign: "middle" });
    s.addText(h2, { x: L + 0.55, y, w: 3.5, h: 0.3, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 12.5, bold: true, color: WHITE, valign: "middle" });
    s.addText(what, { x: L + 4.15, y: y - 0.04, w: 3.8, h: 0.78, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 9, color: "9CACBA", valign: "top", lineSpacing: 12 });
    s.addText(taught, { x: 8.9, y: y - 0.04, w: 3.8, h: 0.78, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 9, color: "6FA8CE", valign: "top", lineSpacing: 12, italic: true });
    y += 0.81;
  });
  s.addNotes("This is the slide that separates me from a candidate who only shows what worked. The pattern across all six is the same: the failure mode that matters is the silent one, where the system looks right and is not. If time is short, tell 01 and 06 and let the slide carry the rest \u2014 06 is the one that connects back to the honesty principle the whole project rests on.");
}

// ================================================================ 14. NOT BUILT
{
  const s = lightSlide();
  chip(s, "14  ·  SCOPE DISCIPLINE");
  title(s, "What I deliberately did not build");
  kicker(s, "Scope discipline is part of the argument, so the omissions are explicit and reasoned rather than quietly absent.", { y: 1.72 });

  const rows = [
    ["A physically accurate CdTe simulator", "Would need real process data. A fake physics model is worse than an honest surrogate."],
    ["Simulated DFPT, electron-phonon or Tc", "Same reason. The hydride module uses published values and builds decisions on top."],
    ["A graphene tactile-sensor use case", "No grounded response model available. Two defensible use cases beat three thin ones."],
    ["Hydride synthesis devices", "No honest way to simulate a hydrogenation anneal. Plans stop where a real lab's seam is."],
    ["A real async task queue", "The state machine is what matters. The infrastructure adds operational surface, not argument."],
    ["A “correct” hydride ranking", "The paper publishes no scores. One ranking as the answer would manufacture authority."],
  ];
  const rh = 0.66, gap = 0.12;
  rows.forEach(([what, why], i) => {
    const y = 2.4 + i * (rh + gap);
    card(s, { x: L, y, w: W, h: rh });
    s.addText("✕", { x: L + 0.26, y, w: 0.3, h: rh, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, bold: true, color: SIGNAL, valign: "middle" });
    s.addText(what, { x: L + 0.68, y, w: 4.5, h: rh, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12.5, bold: true, color: INK, valign: "middle" });
    s.addText(why, { x: L + 5.3, y, w: 6.5, h: rh, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11.5, color: MUTED, valign: "middle" });
  });
  s.addNotes("Every row is a judgment call I would defend. In a real programme, deciding what not to build is most of the job.");
}

// ================================================================ 15. CLOSE
{
  const s = darkSlide();
  chip(s, "15  ·  WHY THIS, WHY ME", { fill: SIGNAL, y: 1.15 });
  s.addText("I am not switching careers.\nI am moving a proven delivery capability into a new domain.", {
    x: L, y: 1.72, w: 11.5, h: 1.3, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 29, bold: true, color: WHITE, valign: "middle", lineSpacing: 40 });

  const bridge = [
    ["Life-science consulting", "A lab's bottleneck is usually its process and feedback loops, not a single technique. Optimizing R&D workflows is what I did."],
    ["0→1 founder", "Built and shipped end to end under ambiguity and resource constraints, owning the outcome. This orchestrator is the same instinct in a new domain."],
    ["Platform growth at scale", "Coordinated engineering, product and data teams, and translated technical work into measurable impact — the research-to-impact translation this work centres on."],
  ];
  const cgap = 0.3, cw = track(3, cgap);
  bridge.forEach(([h2, d], i) => {
    const x = L + i * (cw + cgap);
    card(s, { x, y: 3.35, w: cw, h: 2.15, fill: "222D38", border: "2F3D4A" });
    s.addText(h2, { x: x + 0.32, y: 3.6, w: cw - 0.64, h: 0.36, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 15, bold: true, color: "6FA8CE", valign: "middle" });
    s.addText(d, { x: x + 0.32, y: 4.04, w: cw - 0.64, h: 1.35, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11, color: "9CACBA", valign: "top", lineSpacing: 15 });
  });

  s.addText("What this prototype adds is the domain-technical layer: I understand the closed loop, the data, and the governance well enough to run programmes in it.",
    { x: L, y: 5.65, w: 11.5, h: 0.6, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 14, color: "C3D0DA", valign: "middle", lineSpacing: 20 });
  s.addText("github.com/dekunsun/ai-to-lab-orchestrator   ·   65 tests   ·   docs/architecture.md",
    { x: L, y: 6.45, w: 11.5, h: 0.35, isTextBox: true, margin: 0,
      fontFace: M, fontSize: 11, color: "7E8E9C" });
  s.addNotes("Close on intent, not on modesty. The seniority question is answered by saying plainly that I am optimizing for direction and team, not title.");
}

pres.writeFile({ fileName: OUT }).then(() => console.log("wrote " + OUT));
