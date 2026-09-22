import type { ReactNode } from "react";
import { Nav } from "@/components/nav";
import { ScrollProgress } from "@/components/scroll-progress";
import { Reveal } from "@/components/reveal";
import { Counter } from "@/components/counters";
import { Terminal } from "@/components/terminal";
import { CodeBlock } from "@/components/code-block";
import { CopyButton } from "@/components/copy-button";
import {
  ArrowRightIcon,
  BoltIcon,
  BookIcon,
  BracketsIcon,
  CheckIcon,
  CopyIcon,
  CubeIcon,
  FlagIcon,
  FlaskIcon,
  GaugeIcon,
  GithubIcon,
  LayersIcon,
  ListIcon,
  PackageIcon,
  RefreshIcon,
  ServersIcon,
  ShieldIcon,
} from "@/components/icons";
import {
  BENCHMARKS,
  CODE_CHOICE,
  CODE_CHOICE_OUT,
  CODE_INSTALL,
  CODE_NOUL,
  CODE_SCORE,
  CODE_SERVER,
  ENDPOINTS,
  LINKS,
  PROVIDERS,
  STATS,
} from "@/lib/data";

const YEAR = new Date().getFullYear();

function Kicker({ children }: { children: ReactNode }) {
  return (
    <Reveal>
      <p className="mb-4 font-mono text-xs font-semibold tracking-[0.22em] text-brand uppercase">
        {children}
      </p>
    </Reveal>
  );
}

function ChapterTitle({ title, className = "" }: { title: string; className?: string }) {
  return (
    <Reveal>
      <h2
        className={`font-mono text-3xl font-semibold tracking-tight text-ink sm:text-4xl ${className}`}
      >
        {title}
      </h2>
    </Reveal>
  );
}

function Lead({ children }: { children: ReactNode }) {
  return (
    <Reveal delay={80}>
      <p className="mt-4 max-w-2xl text-lg text-mut">{children}</p>
    </Reveal>
  );
}

function Sunken({ children }: { children: ReactNode }) {
  return (
    <Reveal delay={120}>
      <div className="mt-4 font-mono text-xs tracking-[0.18em] text-mut uppercase">
        {children}
      </div>
    </Reveal>
  );
}

const ECE_MAX = 0.35;

export default function Home() {
  return (
    <div id="top" className="min-h-screen">
      <ScrollProgress />
      <Nav />

      {/* ============ HERO ============ */}
      <section className="relative overflow-hidden pt-32 pb-20 sm:pt-40 sm:pb-28">
        <div className="grid-faint pointer-events-none absolute inset-0" aria-hidden />
        <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
          <div className="grid items-center gap-14 lg:grid-cols-2">
            <div>
              <Reveal>
                <div className="mb-6 inline-flex flex-wrap items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5">
                  <span className="font-mono text-xs text-mut">
                    v0.1.3 · MIT · Python 3.10–3.13
                  </span>
                  <span className="h-3 w-px bg-line" aria-hidden />
                  <span className="flex items-center gap-1.5 font-mono text-xs text-flame">
                    <FlagIcon className="h-3.5 w-3.5" />
                    zero runtime deps
                  </span>
                </div>
              </Reveal>
              <Reveal delay={60}>
                <h1 className="font-mono text-4xl font-bold leading-[1.12] tracking-tight text-ink sm:text-5xl lg:text-6xl">
                  Decisions as{" "}
                  <span className="text-brand">data</span>,{" "}
                  <br />
                  not prose.
                </h1>
              </Reveal>
              <Reveal delay={140}>
                <p className="mt-6 max-w-xl text-lg leading-8 text-mut">
                  tydex turns any LLM into a decision engine.{" "}
                  <code className="font-mono text-[0.9em] text-ink">choice</code>,{" "}
                  <code className="font-mono text-[0.9em] text-ink">score</code>, and{" "}
                  <code className="font-mono text-[0.9em] text-ink">noul</code> return JSON
                  with calibrated probabilities and confidence — one model call, greedy
                  decoding, built on your existing provider.
                </p>
              </Reveal>
              <Reveal delay={220}>
                <div className="mt-8 flex flex-wrap items-center gap-3">
                  <a
                    href="#install"
                    className="inline-flex h-12 cursor-pointer items-center gap-2 rounded-xl bg-flame px-5 text-base font-semibold text-white shadow-lg shadow-flame/25 transition-all duration-200 hover:shadow-flame/40"
                  >
                    <PackageIcon className="h-5 w-5" />
                    Get started
                  </a>
                  <a
                    href={LINKS.docs}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex h-12 cursor-pointer items-center gap-2 rounded-xl border border-line bg-surface px-5 text-base font-semibold text-ink transition-colors duration-200 hover:border-brand/50 hover:text-brand"
                  >
                    <BookIcon className="h-5 w-5" />
                    Read the docs
                  </a>
                  <a
                    href={LINKS.github}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="tydex on GitHub"
                    className="inline-flex h-12 w-12 cursor-pointer items-center justify-center rounded-xl border border-line bg-surface text-ink transition-colors duration-200 hover:text-brand"
                  >
                    <GithubIcon className="h-5 w-5" />
                  </a>
                </div>
              </Reveal>
              <Reveal delay={300}>
                <p className="mt-6 font-mono text-xs text-mut">
                  pip install tydex &nbsp;·&nbsp; python ≥ 3.10 &nbsp;·&nbsp;{" "}
                  {PROVIDERS.length} providers
                </p>
              </Reveal>
            </div>

            <Reveal delay={120} className="lg:pl-2">
              <Terminal
                prompt="$"
                lines={[
                  { type: "prompt", text: "python - <<EOF" },
                  { type: "plain", text: "from tydex import Tydex" },
                  { type: "plain", text: "from tydex.backends import MockBackend" },
                  { type: "plain", text: "tdex = Tydex(MockBackend())" },
                  { type: "plain", text: "" },
                  { type: "plain", text: "r = tdex.choice(" },
                  { type: "plain", text: "    state=\"Cart returned HTTP 503\"," },
                  { type: "plain", text: "    options=[\"Retry\",\"Degrade\",\"Escalate\"]," },
                  { type: "plain", text: ")" },
                  { type: "prompt", text: "print(r)" },
                  { type: "out", text: "ChoiceResult(" },
                  { type: "out", text: "  choice='Escalate'," },
                  { type: "out", text: "  probabilities={'Retry': 0.10," },
                  { type: "out", text: "                'Degrade': 0.22," },
                  { type: "out", text: "                'Escalate': 0.68}," },
                  { type: "out", text: "  confidence=0.68, source='self')" },
                ]}
              />
            </Reveal>
          </div>
        </div>
      </section>

      {/* ============ STATS STRIP ============ */}
      <section className="border-y border-line bg-surface">
        <div className="mx-auto grid max-w-6xl grid-cols-2 gap-8 px-4 py-12 sm:px-6 lg:grid-cols-4">
          {STATS.map((s) => (
            <Counter key={s.label} value={s.value} suffix={s.suffix} label={s.label} />
          ))}
        </div>
      </section>

      {/* ============ 01 · PROBLEM ============ */}
      <section className="relative py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Kicker>01 · the problem</Kicker>
          <ChapterTitle title="LLMs answer in prose. Your app needs a decision." />
          <Lead>
            Prompting a chat model for a decision leaves you with paragraphs, markdown
            lists, and borrowed confidence. Every downstream system pays the price.
          </Lead>

          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {[
              {
                icon: <BracketsIcon className="h-5 w-5" />,
                title: "Parsing fragility",
                body: "Regex over bullet points to recover a single answer. One reworded prompt and your pipeline breaks silently.",
              },
              {
                icon: <GaugeIcon className="h-5 w-5" />,
                title: "Confidence theater",
                body: "\"I'm 99% sure\" ignores calibration. Unfitted probabilities are not decision inputs — they're noise.",
              },
              {
                icon: <BoltIcon className="h-5 w-5" />,
                title: "Multi-turn tug",
                body: "Reasoning loops and tool chains multiply token spend. A single greedy call with a schema is enough for most decisions.",
              },
            ].map((card, i) => (
              <Reveal key={card.title} delay={i * 90}>
                <div className="group h-full rounded-2xl border border-line bg-surface p-6 transition-shadow duration-300 hover:shadow-xl hover:shadow-brand/5">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-soft text-brand">
                    {card.icon}
                  </div>
                  <h3 className="mt-5 font-mono text-lg font-semibold text-ink">
                    {card.title}
                  </h3>
                  <p className="mt-2.5 text-sm leading-6 text-mut">{card.body}</p>
                </div>
              </Reveal>
            ))}
          </div>

          <Reveal delay={140}>
            <div className="mt-12 overflow-hidden rounded-2xl border border-line bg-surface">
              <div className="grid md:grid-cols-2">
                <div className="border-b border-line p-6 md:border-r md:border-b-0">
                  <div className="font-mono text-xs font-semibold tracking-widest text-mut uppercase">
                    raw model output
                  </div>
                  <p className="mt-3 font-mono text-sm leading-6 text-mut">
                    &ldquo;Based on my analysis I would recommend escalating this to an on-call
                    engineer for further investigation, as the payment provider is
                    possibly rate-limiting the upstream integration&hellip;&rdquo;
                  </p>
                  <p className="mt-4 font-mono text-xs text-flame">→ needs parsing</p>
                </div>
                <div className="p-6">
                  <div className="font-mono text-xs font-semibold tracking-widest text-mut uppercase">
                    tydex output
                  </div>
                  <pre className="mt-3 overflow-x-auto font-mono text-sm leading-6">
                    <code className="text-ink">
                      <span className="text-tk-k">{"{"}</span>
                      {"\n  "}<span className="text-tk-k">&quot;choice&quot;</span>
                      <span className="text-tk-n">: &quot;Escalate&quot;</span>
                      <span className="text-tk-c">,</span>
                      {"\n  "}<span className="text-tk-k">&quot;probability&quot;</span>
                      <span className="text-tk-n">: 0.68</span>
                      <span className="text-tk-c">,</span>
                      {"\n  "}<span className="text-tk-k">&quot;confidence&quot;</span>
                      <span className="text-tk-n">: 0.68</span>
                      {"\n"}
                      <span className="text-tk-k">{"}"}</span>
                    </code>
                  </pre>
                  <p className="mt-4 flex items-center gap-2 font-mono text-xs text-brand">
                    <CheckIcon className="h-4 w-4" /> ready for typed code
                  </p>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ============ 02 · PRIMITIVES ============ */}
      <section id="primitives" className="border-t border-line bg-surface py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Kicker>02 · the primitives</Kicker>
          <ChapterTitle title="Three operators. Every decision." />
          <Lead>
            Each primitive is one model call that returns a schema-enforced result with a
            probability distribution — from provider logprobs when available, else a
            calibrated self-estimate.
          </Lead>

          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {[
              {
                icon: <ListIcon className="h-5 w-5" />,
                name: "choice",
                sig: "choice(state, options)",
                body: "Pick the best option from a list. Returns a full probability distribution over every option.",
                tags: ["≥ 2 options", "≤ 20 options"],
              },
              {
                icon: <CubeIcon className="h-5 w-5" />,
                name: "score",
                sig: "score(state, levels)",
                body: "Rate a state against ordinal levels — OK / Degraded / Critical, 1–5, reject / accept.",
                tags: ["ordinal levels", "ordinal voting"],
              },
              {
                icon: <FlagIcon className="h-5 w-5" />,
                name: "noul",
                sig: "noul(state, statement)",
                body: "A yes/no binary decision with a true probability — the building block of checks and gates.",
                tags: ["p(statement)", "binary"],
              },
            ].map((p, i) => (
              <Reveal key={p.name} delay={i * 90}>
                <div className="flex h-full flex-col rounded-2xl border border-line bg-bg p-6 transition-shadow duration-300 hover:shadow-xl hover:shadow-brand/5">
                  <div className="flex items-center justify-between">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-soft text-brand">
                      {p.icon}
                    </div>
                    <span className="font-mono text-2xl font-bold text-ink/10">0{i + 1}</span>
                  </div>
                  <h3 className="mt-5 font-mono text-xl font-semibold text-ink">{p.name}</h3>
                  <code className="mt-1 block w-fit rounded-md bg-raise px-2 py-0.5 font-mono text-xs text-brand">
                    {p.sig}
                  </code>
                  <p className="mt-3 flex-1 text-sm leading-6 text-mut">{p.body}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {p.tags.map((t) => (
                      <span
                        key={t}
                        className="rounded-full border border-line px-2.5 py-0.5 font-mono text-[11px] text-mut"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </Reveal>
            ))}
          </div>

          <Reveal delay={120}>
            <div className="mt-12 space-y-5">
              <CodeBlock
                label="choice · one call, JSON mode"
                code={CODE_CHOICE}
                output={CODE_CHOICE_OUT}
              />
              <div className="grid gap-5 md:grid-cols-2">
                <CodeBlock label="score" code={CODE_SCORE} />
                <CodeBlock label="noul" code={CODE_NOUL} />
              </div>
            </div>
          </Reveal>

          <Sunken>
            results: ChoiceResult · ScoreResult · NoulResult — {`{ choice|score|probability, probabilities, confidence, source }`}
          </Sunken>
        </div>
      </section>

      {/* ============ 03 · CALIBRATION ============ */}
      <section id="calibration" className="py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Kicker>03 · calibration</Kicker>
          <ChapterTitle title="Probability you can act on." />
          <Lead>
            Measured on {BENCHMARKS.reduce((a, b) => a + b.samples, 0)} labeled tickets with
            gemma4:31b. Temperature scaling fitted on a held-out split drops expected
            calibration error by up to{" "}
            <span className="font-mono font-semibold text-flame">15×</span>.
          </Lead>

          <div className="mt-12 grid gap-5 lg:grid-cols-3">
            {BENCHMARKS.map((b, i) => (
              <Reveal key={b.id} delay={i * 90}>
                <div className="rounded-2xl border border-line bg-surface p-6">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-lg font-semibold text-ink">
                      {b.name}
                    </span>
                    <span className="font-mono text-xs text-mut">T = {b.temp}</span>
                  </div>
                  <div className="mt-6 space-y-4">
                    <div className="flex items-center gap-3">
                      <span className="w-16 shrink-0 font-mono text-xs text-mut">
                        before
                      </span>
                      <div className="h-2.5 flex-1 rounded-full bg-raise">
                        <div
                          className="h-full rounded-full bg-mut/40 transition-[width] duration-700"
                          style={{ width: `${(b.before / ECE_MAX) * 100}%` }}
                        />
                      </div>
                      <span className="w-14 shrink-0 text-right font-mono text-sm text-mut tabular-nums">
                        {b.before.toFixed(3)}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="w-16 shrink-0 font-mono text-xs text-brand">
                        after
                      </span>
                      <div className="h-2.5 flex-1 rounded-full bg-raise">
                        <div
                          className="h-full rounded-full bg-flame transition-[width] duration-700"
                          style={{ width: `${(b.after / ECE_MAX) * 100}%` }}
                        />
                      </div>
                      <span className="w-14 shrink-0 text-right font-mono text-sm font-semibold text-brand tabular-nums">
                        {b.after.toFixed(3)}
                      </span>
                    </div>
                  </div>
                  <p className="mt-5 font-mono text-xs text-mut">
                    ECE · expected calibration error
                  </p>
                </div>
              </Reveal>
            ))}
          </div>

          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {[
              {
                icon: <FlaskIcon className="h-5 w-5" />,
                title: "Measured, not assumed",
                body: "An evaluation harness (Ladder Test) plus a 60-ticket labeled set scores every change against ground truth.",
              },
              {
                icon: <RefreshIcon className="h-5 w-5" />,
                title: "Self-healing loop",
                body: "Recorder → labeled feedback → isotonic/auto re-fit. The server can re-calibrate without redeploying.",
              },
              {
                icon: <ShieldIcon className="h-5 w-5" />,
                title: "Escalate with evidence",
                body: "RoutedTydex hands low-confidence outcomes to a human (a tier) instead of guessing — with full provenance.",
              },
            ].map((c, i) => (
              <Reveal key={c.title} delay={i * 90}>
                <div className="h-full rounded-2xl border border-line bg-surface p-6">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-soft text-brand">
                    {c.icon}
                  </div>
                  <h3 className="mt-5 font-mono text-lg font-semibold text-ink">
                    {c.title}
                  </h3>
                  <p className="mt-2.5 text-sm leading-6 text-mut">{c.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ============ 04 · ARCHITECTURE ============ */}
      <section id="architecture" className="border-t border-line bg-surface py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Kicker>04 · production architecture</Kicker>
          <ChapterTitle title="From idea to inference at scale." />
          <Lead>
            tydex ships a batteries-included stack: an async FastAPI server, an
            intelligence layer on top of the core primitives, and durable storage for the
            feedback loop.
          </Lead>

          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {[
              {
                icon: <ServersIcon className="h-5 w-5" />,
                title: "Async FastAPI server",
                body: "Typed JSON endpoints, API-key auth, CORS, rate limiting, structured logging and response caching. OpenAPI at /docs.",
              },
              {
                icon: <LayersIcon className="h-5 w-5" />,
                title: "EnsembleTydex",
                body: "Aggregate several backends as a weighted ensemble; probabilities are merged per option, optionally tuned by per-member weights.",
              },
              {
                icon: <RefreshIcon className="h-5 w-5" />,
                title: "RefiningTydex",
                body: "Below a confidence threshold, the model re-reviews state and options, and both passes are averaged into the final distribution.",
              },
              {
                icon: <ShieldIcon className="h-5 w-5" />,
                title: "Feedback store",
                body: "Decisions, probabilities and labels persist to SQLite. Labels feed AutoCalibrator.maybe_refit for continuous self-correction.",
              },
              {
                icon: <GaugeIcon className="h-5 w-5" />,
                title: "Auto-calibration",
                body: "Isotonic and temperature-scaled calibrators, tiered routing with RequiresHuman escalation for low-confidence calls.",
              },
              {
                icon: <FlaskIcon className="h-5 w-5" />,
                title: "Evaluation harness",
                body: "Ladder Test benchmarks the whole stack on 60 labeled tickets and exposes ECE before/after every calibration change.",
              },
            ].map((f, i) => (
              <Reveal key={f.title} delay={(i % 3) * 90}>
                <div className="h-full rounded-2xl border border-line bg-bg p-6 transition-shadow duration-300 hover:shadow-xl hover:shadow-brand/5">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-soft text-brand">
                    {f.icon}
                  </div>
                  <h3 className="mt-5 font-mono text-lg font-semibold text-ink">
                    {f.title}
                  </h3>
                  <p className="mt-2.5 text-sm leading-6 text-mut">{f.body}</p>
                </div>
              </Reveal>
            ))}
          </div>

          <Reveal delay={100}>
            <div className="mt-12 flex flex-wrap items-center gap-3">
              <span className="font-mono text-xs tracking-widest text-mut uppercase">
                run it
              </span>
              {ENDPOINTS.map((e) => (
                <span
                  key={e.path}
                  className="inline-flex items-center gap-2 rounded-full border border-line bg-bg px-3 py-1.5"
                >
                  <span
                    className={`font-mono text-[11px] font-bold ${
                      e.method === "GET" ? "text-brand" : "text-flame"
                    }`}
                  >
                    {e.method}
                  </span>
                  <code className="font-mono text-xs text-ink">{e.path}</code>
                </span>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* ============ 05 · GET STARTED ============ */}
      <section id="install" className="py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Kicker>05 · get started</Kicker>
          <ChapterTitle title="Live in five lines." />
          <Lead>
            Install from PyPI, or run the container from GHCR. No runtime dependencies in
            the core — the async server needs two optional extras.
          </Lead>

          <div className="mt-12 grid gap-5 lg:grid-cols-2">
            <Reveal>
              <div className="overflow-hidden rounded-2xl border border-line bg-surface">
                <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
                  <span className="font-mono text-xs font-medium text-mut">
                    install · terminal
                  </span>
                  <CopyButton text={`${CODE_INSTALL}\n`} label="install" />
                </div>
                <pre className="overflow-x-auto p-5 font-mono text-sm leading-6">
                  <code className="text-ink">
                    <span className="text-tk-c">$</span> <span className="text-brand">pip install</span>{" "}
                    <span className="text-tk-s">tydex</span>
                  </code>
                </pre>
              </div>
            </Reveal>
            <Reveal delay={100}>
              <CodeBlock label="server · async FastAPI" code={CODE_SERVER} />
            </Reveal>
          </div>

          <Reveal delay={80}>
            <div className="mt-12 grid gap-5 md:grid-cols-2">
              <div className="rounded-2xl border border-line bg-surface p-6">
                <h3 className="font-mono text-sm font-semibold tracking-widest text-mut uppercase">
                  runs anywhere
                </h3>
                <ul className="mt-4 space-y-3 text-sm text-ink">
                  <li className="flex items-center gap-3">
                    <CheckIcon className="h-4 w-4 shrink-0 text-brand" />
                    wheel on PyPI —{" "}
                    <code className="font-mono text-xs">pip install tydex</code>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckIcon className="h-4 w-4 shrink-0 text-brand" />
                    Docker image —{" "}
                    <code className="font-mono text-xs">
                      docker pull ghcr.io/dracko000/tydex
                    </code>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckIcon className="h-4 w-4 shrink-0 text-brand" />
                    CLI included —{" "}
                    <code className="font-mono text-xs">tydex providers</code>
                  </li>
                </ul>
              </div>
              <div className="rounded-2xl border border-line bg-surface p-6">
                <h3 className="font-mono text-sm font-semibold tracking-widest text-mut uppercase">
                  public artifacts
                </h3>
                <div className="mt-4 flex flex-wrap gap-x-3 gap-y-2">
                  <a href={LINKS.pypi} target="_blank" rel="noopener noreferrer">
                    <img
                      src="https://img.shields.io/pypi/v/tydex.svg"
                      alt="PyPI version"
                      className="h-6"
                    />
                  </a>
                  <a href={LINKS.pypi} target="_blank" rel="noopener noreferrer">
                    <img
                      src="https://img.shields.io/pypi/pyversions/tydex.svg"
                      alt="Python versions"
                      className="h-6"
                    />
                  </a>
                  <a href="https://opensource.org/licenses/MIT" target="_blank" rel="noopener noreferrer">
                    <img
                      src="https://img.shields.io/pypi/l/tydex.svg"
                      alt="License MIT"
                      className="h-6"
                    />
                  </a>
                  <a href={LINKS.github} target="_blank" rel="noopener noreferrer">
                    <img
                      src="https://img.shields.io/github/actions/workflow/status/Dracko000/tydex/ci.yml?branch=main&label=CI"
                      alt="CI"
                      className="h-6"
                    />
                  </a>
                  <a href={LINKS.releases} target="_blank" rel="noopener noreferrer">
                    <img
                      src="https://img.shields.io/github/v/release/Dracko000/tydex"
                      alt="GitHub release"
                      className="h-6"
                    />
                  </a>
                  <a href={LINKS.docs} target="_blank" rel="noopener noreferrer">
                    <img
                      src="https://img.shields.io/badge/docs-live-2ea44f"
                      alt="Docs live"
                      className="h-6"
                    />
                  </a>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ============ CLIMAX CTA ============ */}
      <section className="pb-24 sm:pb-32">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Reveal>
            <div className="relative overflow-hidden rounded-3xl border border-line bg-surface px-6 py-14 text-center sm:px-12">
              <div className="grid-faint pointer-events-none absolute inset-0" aria-hidden />
              <div className="relative">
                <BoltIcon className="mx-auto h-10 w-10 text-flame" />
                <h2 className="mt-4 font-mono text-3xl font-bold tracking-tight text-ink sm:text-4xl">
                  Stop parsing prose.
                  <br />
                  Start making decisions.
                </h2>
                <p className="mx-auto mt-4 max-w-xl text-mut">
                  Same model, same call — but the answer arrives as calibrated data you
                  can compute on, escalate, or log.
                </p>
                <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                  <a
                    href={LINKS.pypi}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex h-12 cursor-pointer items-center gap-2 rounded-xl bg-flame px-5 text-base font-semibold text-white shadow-lg shadow-flame/25 transition-all duration-200 hover:shadow-flame/40"
                  >
                    <CopyIcon className="h-5 w-5" />
                    pip install tydex
                  </a>
                  <a
                    href={LINKS.github}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex h-12 cursor-pointer items-center gap-2 rounded-xl border border-line bg-bg px-5 text-base font-semibold text-ink transition-colors duration-200 hover:text-brand"
                  >
                    <GithubIcon className="h-5 w-5" />
                    Star on GitHub
                    <ArrowRightIcon className="h-4 w-4" />
                  </a>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ============ FOOTER ============ */}
      <footer className="border-t border-line bg-surface">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
          <div className="grid gap-10 md:grid-cols-4">
            <div className="md:col-span-2">
              <div className="flex items-center gap-2.5">
                <BoltIcon className="h-5 w-5 text-brand" />
                <span className="font-mono text-lg font-semibold text-ink">tydex</span>
              </div>
              <p className="mt-3 max-w-sm text-sm text-mut">
                Typed decision primitives for LLMs. Built as data, kept calibrated,
                shipped as a library.
              </p>
              <p className="mt-4 font-mono text-xs text-mut">
                © {YEAR} tydex · MIT License · v0.1.3
              </p>
            </div>
            <div>
              <div className="font-mono text-xs font-semibold tracking-widest text-mut uppercase">
                Product
              </div>
              <ul className="mt-3 space-y-2 text-sm">
                <li><a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href="#primitives">Primitives</a></li>
                <li><a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href="#calibration">Calibration</a></li>
                <li><a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href="#architecture">Architecture</a></li>
                <li><a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href="#install">Install</a></li>
              </ul>
            </div>
            <div>
              <div className="font-mono text-xs font-semibold tracking-widest text-mut uppercase">
                Ecosystem
              </div>
              <ul className="mt-3 space-y-2 text-sm">
                <li>
                  <a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href={LINKS.docs} target="_blank" rel="noopener noreferrer">
                    Documentation
                  </a>
                </li>
                <li>
                  <a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href={LINKS.pypi} target="_blank" rel="noopener noreferrer">
                    PyPI
                  </a>
                </li>
                <li>
                  <a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href={LINKS.ghcr} target="_blank" rel="noopener noreferrer">
                    GHCR image
                  </a>
                </li>
                <li>
                  <a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href={LINKS.changelog} target="_blank" rel="noopener noreferrer">
                    Changelog
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}