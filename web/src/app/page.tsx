import type { ReactNode } from "react";
import { LiftedLink } from "@/components/motion-link";
import { Nav } from "@/components/nav";
import { ScrollProgress } from "@/components/scroll-progress";
import { Reveal } from "@/components/reveal";
import { Counter } from "@/components/counters";
import { Terminal } from "@/components/terminal";
import { CodeBlock } from "@/components/code-block";
import { CalibrationCharts } from "@/components/calibration-charts";
import { VsJevChat } from "@/components/vs-jev-chat";
import { VsJevChart } from "@/components/vs-jev-chart";
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

function ChapterTitle({ title }: { title: string }) {
  return (
    <Reveal>
      <h2 className="font-mono text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
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

function Section({
  id,
  title,
  kicker,
  lead,
  children,
  tone,
}: {
  id?: string;
  title: string;
  kicker: string;
  lead?: ReactNode;
  children: ReactNode;
  tone?: "raised";
}) {
  return (
    <section
      id={id}
      className={`${tone === "raised" ? "border-y border-line bg-surface/40" : ""} py-24 sm:py-28`}
    >
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <Kicker>{kicker}</Kicker>
        <ChapterTitle title={title} />
        {lead ? <Lead>{lead}</Lead> : null}
        <div className="mt-12">{children}</div>
      </div>
    </section>
  );
}

function Hairgrid({
  columns,
  children,
}: {
  columns: string;
  children: ReactNode;
}) {
  return (
    <div className={`grid bg-line gap-px border border-line ${columns}`}>
      {children}
    </div>
  );
}

function Cell({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`bg-bg p-6 lg:p-8 ${className}`}>{children}</div>;
}

function MonoSub({ children }: { children: ReactNode }) {
  return (
    <p className="mt-2.5 text-sm leading-6 text-mut">{children}</p>
  );
}

function EndpointText() {
  return (
    <p className="mt-8 font-mono text-sm leading-8 text-mut">
      {ENDPOINTS.map((e, i) => (
        <span key={e.path}>
          <span className={e.method === "GET" ? "text-brand" : "text-flame"}>
            {e.method}
          </span>{" "}
          <span className="text-ink">{e.path}</span>
          {i < ENDPOINTS.length - 1 ? <span className="text-line"> &#47;·&#47; </span> : null}
        </span>
      ))}
    </p>
  );
}

export default function Home() {
  return (
    <div id="top" className="min-h-screen">
      <ScrollProgress />
      <Nav />

      {/* ============ HERO ============ */}
      <section className="relative overflow-hidden pt-32 pb-20 sm:pt-40 sm:pb-24">
        <div className="grid-faint pointer-events-none absolute inset-0" aria-hidden />
        <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
          <div className="grid items-center gap-14 lg:grid-cols-2">
            <div>
              <Reveal>
                <div className="mb-6 inline-flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="font-mono text-xs text-mut">
                    v0.1.3 · MIT · Python 3.10–3.13
                  </span>
                </div>
              </Reveal>
              <Reveal delay={60}>
                <h1 className="font-mono text-4xl font-bold leading-[1.12] tracking-tight text-ink sm:text-5xl lg:text-6xl">
                  Decisions as <span className="text-brand">data</span>,{" "}
                  <br />
                  not prose.
                </h1>
              </Reveal>
              <Reveal delay={140}>
                <p className="mt-6 max-w-xl text-lg leading-8 text-mut">
                  tydex turns any LLM into a decision engine.{" "}
                  <code className="font-mono text-[0.9em] text-ink">choice</code>,{" "}
                  <code className="font-mono text-[0.9em] text-ink">score</code>, and{" "}
                  <code className="font-mono text-[0.9em] text-ink">noul</code> return
                  JSON with calibrated probabilities and confidence — one model call,
                  greedy decoding, built on your existing provider.
                </p>
              </Reveal>
              <Reveal delay={220}>
                <div className="mt-8 flex flex-wrap items-center gap-3">
                  <LiftedLink
                    href="#install"
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.98 }}
                    className="inline-flex h-12 cursor-pointer items-center gap-2 rounded-xl bg-flame px-5 text-base font-semibold text-white shadow-lg shadow-flame/25 transition-colors duration-200 hover:shadow-flame/40"
                  >
                    <PackageIcon className="h-5 w-5" />
                    Get started
                  </LiftedLink>
                  <a
                    href={LINKS.docs}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex h-12 cursor-pointer items-center gap-2 rounded-xl border border-line px-5 text-base font-semibold text-ink transition-colors duration-200 hover:text-brand"
                  >
                    <BookIcon className="h-5 w-5" />
                    Read the docs
                  </a>
                  <a
                    href={LINKS.github}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="tydex on GitHub"
                    className="inline-flex h-12 w-12 cursor-pointer items-center justify-center rounded-xl border border-line text-ink transition-colors duration-200 hover:text-brand"
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
      <section className="border-y border-line">
        <div className="mx-auto grid max-w-6xl grid-cols-2 gap-x-8 gap-y-10 px-4 py-12 sm:px-6 lg:grid-cols-4">
          {STATS.map((s) => (
            <Counter key={s.label} value={s.value} suffix={s.suffix} label={s.label} />
          ))}
        </div>
      </section>

      {/* ============ 01 · PROBLEM ============ */}
      <Section
        kicker="01 · the problem"
        title="LLMs answer in prose. Your app needs a decision."
        lead={
          <>
            Prompting a chat model for a decision leaves you with paragraphs, markdown
            lists, and borrowed confidence. Every downstream system pays the price.
          </>
        }
      >
        <Hairgrid columns="md:grid-cols-3">
          <Reveal>
            <Cell>
              <BracketsIcon className="h-6 w-6 text-brand" />
              <h3 className="mt-5 font-mono text-lg font-semibold text-ink">
                Parsing fragility
              </h3>
              <MonoSub>
                Regex over bullet points to recover a single answer. One reworded prompt
                and your pipeline breaks silently.
              </MonoSub>
            </Cell>
          </Reveal>
          <Reveal delay={90}>
            <Cell>
              <GaugeIcon className="h-6 w-6 text-brand" />
              <h3 className="mt-5 font-mono text-lg font-semibold text-ink">
                Confidence theater
              </h3>
              <MonoSub>
                &ldquo;I&rsquo;m 99% sure&rdquo; ignores calibration. Unfitted probabilities
                are not decision inputs — they&rsquo;re noise.
              </MonoSub>
            </Cell>
          </Reveal>
          <Reveal delay={180}>
            <Cell>
              <BoltIcon className="h-6 w-6 text-brand" />
              <h3 className="mt-5 font-mono text-lg font-semibold text-ink">
                Multi-turn tug
              </h3>
              <MonoSub>
                Reasoning loops and tool chains multiply token spend. A single greedy call
                with a schema is enough for most decisions.
              </MonoSub>
            </Cell>
          </Reveal>
        </Hairgrid>

        <div className="mt-16 grid gap-8 lg:grid-cols-2 lg:gap-0 lg:divide-x lg:divide-line">
          <div className="lg:pr-10">
            <Reveal>
              <p className="font-mono text-xs font-semibold tracking-widest text-mut uppercase">
                raw model output
              </p>
              <p className="mt-4 font-mono text-sm leading-7 text-mut">
                &ldquo;Based on my analysis I would recommend escalating this to an
                on-call engineer for further investigation, as the payment provider is
                possibly rate-limiting the upstream integration&hellip;&rdquo;
              </p>
              <p className="mt-4 font-mono text-xs text-flame">→ needs parsing</p>
            </Reveal>
          </div>
          <div className="pt-8 lg:pl-10 lg:pt-0">
            <Reveal delay={80}>
              <p className="font-mono text-xs font-semibold tracking-widest text-mut uppercase">
                tydex output
              </p>
              <pre className="mt-4 font-mono text-sm leading-7">
                <code className="text-tk-n">
                  {`{
  "choice": "Escalate",
  "probability": 0.68,
  "confidence": 0.68
}`}
                </code>
              </pre>
              <p className="mt-4 flex items-center gap-2 font-mono text-xs text-brand">
                <CheckIcon className="h-4 w-4" /> ready for typed code
              </p>
            </Reveal>
          </div>
        </div>
      </Section>

      {/* ============ 02 · PRIMITIVES ============ */}
      <Section
        id="primitives"
        tone="raised"
        kicker="02 · the primitives"
        title="Three operators. Every decision."
        lead={
          <>
            Each primitive is one model call that returns a schema-enforced result with a
            probability distribution — from provider logprobs when available, else a
            calibrated self-estimate.
          </>
        }
      >
        <Hairgrid columns="md:grid-cols-3">
          {[
            {
              icon: <ListIcon className="h-6 w-6 text-brand" />,
              num: "01",
              name: "choice",
              sig: "choice(state, options)",
              body: "Pick the best option from a list. Returns a full probability distribution over every option.",
              tags: "≥ 2 options · ≤ 20 options",
            },
            {
              icon: <CubeIcon className="h-6 w-6 text-brand" />,
              num: "02",
              name: "score",
              sig: "score(state, levels)",
              body: "Rate a state against ordinal levels — OK / Degraded / Critical, 1–5, reject / accept.",
              tags: "ordinal levels",
            },
            {
              icon: <FlagIcon className="h-6 w-6 text-brand" />,
              num: "03",
              name: "noul",
              sig: "noul(state, statement)",
              body: "A yes/no binary decision with a true probability — the building block of checks and gates.",
              tags: "p(statement) · binary",
            },
          ].map((p, i) => (
            <Reveal key={p.name} delay={i * 80}>
              <Cell>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {p.icon}
                    <h3 className="font-mono text-xl font-semibold text-ink">{p.name}</h3>
                  </div>
                  <span className="font-mono text-2xl font-bold text-ink/10">{p.num}</span>
                </div>
                <code className="mt-4 block font-mono text-sm text-brand">{p.sig}</code>
                <MonoSub>{p.body}</MonoSub>
                <p className="mt-4 font-mono text-xs text-mut">{p.tags}</p>
              </Cell>
            </Reveal>
          ))}
        </Hairgrid>

        <div className="mt-16 space-y-6">
          <Reveal>
            <CodeBlock
              label="choice · one call, JSON mode"
              code={CODE_CHOICE}
              output={CODE_CHOICE_OUT}
            />
          </Reveal>
          <div className="grid gap-6 lg:grid-cols-2">
            <Reveal>
              <CodeBlock label="score" code={CODE_SCORE} />
            </Reveal>
            <Reveal delay={80}>
              <CodeBlock label="noul" code={CODE_NOUL} />
            </Reveal>
          </div>
        </div>

        <Reveal delay={120}>
          <p className="mt-8 font-mono text-xs tracking-[0.18em] text-mut uppercase">
            results: ChoiceResult · ScoreResult · NoulResult
          </p>
        </Reveal>
      </Section>

      {/* ============ 03 · CALIBRATION ============ */}
      <Section
        id="calibration"
        kicker="03 · calibration"
        title="Probability you can act on."
        lead={
          <>
            Measured on {BENCHMARKS.reduce((a, b) => a + b.samples, 0)} labeled tickets
            with gemma4:31b. Temperature scaling fitted on a held-out split drops
            expected calibration error by up to{" "}
            <span className="font-mono font-semibold text-flame">15×</span>.
          </>
        }
      >
        <CalibrationCharts />
        <Reveal delay={80}>
          <p className="mt-6 font-mono text-xs text-mut">
            ECE · expected calibration error — temperature fitted per primitive,{" "}
            {BENCHMARKS.reduce((a, b) => a + b.samples, 0)} labeled tickets
          </p>
        </Reveal>

        <div className="mt-16 grid gap-8 lg:grid-cols-3 lg:gap-0 lg:divide-x lg:divide-line">
          {[
            {
              icon: <FlaskIcon className="h-6 w-6 text-brand" />,
              title: "Measured, not assumed",
              body: "An evaluation harness (Ladder Test) plus a 60-ticket labeled set scores every change against ground truth.",
            },
            {
              icon: <RefreshIcon className="h-6 w-6 text-brand" />,
              title: "Self-healing loop",
              body: "Recorder → labeled feedback → isotonic/auto re-fit. The server can re-calibrate without redeploying.",
            },
            {
              icon: <ShieldIcon className="h-6 w-6 text-brand" />,
              title: "Escalate with evidence",
              body: "RoutedTydex hands low-confidence outcomes to a human (a tier) instead of guessing — with full provenance.",
            },
          ].map((c, i) => (
            <Reveal key={c.title} delay={i * 80} className={i > 0 ? "pt-8 lg:pt-0 lg:pl-10" : "lg:pr-10"}>
              <h3 className="flex items-center gap-3 font-mono text-lg font-semibold text-ink">
                {c.icon}
                {c.title}
              </h3>
              <p className="mt-3 text-sm leading-6 text-mut">{c.body}</p>
            </Reveal>
          ))}
        </div>
      </Section>

      {/* ============ 04 · ARCHITECTURE ============ */}
      <Section
        id="architecture"
        tone="raised"
        kicker="04 · production architecture"
        title="From idea to inference at scale."
        lead={
          <>
            tydex ships a batteries-included stack: an async FastAPI server, an
            intelligence layer on top of the core primitives, and durable storage for the
            feedback loop.
          </>
        }
      >
        <Hairgrid columns="sm:grid-cols-2 lg:grid-cols-3">
          {[
            {
              icon: <ServersIcon className="h-6 w-6 text-brand" />,
              title: "Async FastAPI server",
              body: "Typed JSON endpoints, API-key auth, CORS, rate limiting, structured logging and response caching. OpenAPI at /docs.",
            },
            {
              icon: <LayersIcon className="h-6 w-6 text-brand" />,
              title: "EnsembleTydex",
              body: "Aggregate several backends as a weighted ensemble; probabilities are merged per option, optionally tuned by per-member weights.",
            },
            {
              icon: <RefreshIcon className="h-6 w-6 text-brand" />,
              title: "RefiningTydex",
              body: "Below a confidence threshold, the model re-reviews state and options, and both passes are averaged into the final distribution.",
            },
            {
              icon: <ShieldIcon className="h-6 w-6 text-brand" />,
              title: "Feedback store",
              body: "Decisions, probabilities and labels persist to SQLite. Labels feed AutoCalibrator.maybe_refit for continuous self-correction.",
            },
            {
              icon: <GaugeIcon className="h-6 w-6 text-brand" />,
              title: "Auto-calibration",
              body: "Isotonic and temperature-scaled calibrators, tiered routing with RequiresHuman escalation for low-confidence calls.",
            },
            {
              icon: <FlaskIcon className="h-6 w-6 text-brand" />,
              title: "Evaluation harness",
              body: "Ladder Test benchmarks the whole stack on 60 labeled tickets and exposes ECE before/after every calibration change.",
            },
          ].map((f, i) => (
            <Reveal key={f.title} delay={(i % 3) * 80}>
              <Cell>
                <h3 className="flex items-center gap-3 font-mono text-lg font-semibold text-ink">
                  {f.icon}
                  {f.title}
                </h3>
                <MonoSub>{f.body}</MonoSub>
              </Cell>
            </Reveal>
          ))}
        </Hairgrid>

        <EndpointText />
      </Section>

      {/* ============ 05 · TYDEX VS JEV ============ */}
      <Section
        id="vs-jev"
        kicker="05 · tydex vs Jev"
        title="The decision engine that inspired tydex — without the walled garden."
        lead={
          <>
            tydex is an open-source behavioural clone of Jev. Same primitives
            ({`choice`} / {`score`} / {`noul`}), same escalation model — but the code,
            the data, and the calibration pipeline stay yours.
          </>
        }
      >
        <div className="grid items-start gap-10 lg:grid-cols-5">
          <div className="lg:col-span-3">
            <VsJevChat />
          </div>
          <div className="lg:col-span-2">
            <Reveal delay={120}>
              <VsJevChart />
            </Reveal>
          </div>
        </div>

        <Reveal delay={80}>
          <p className="mt-8 font-mono text-xs text-mut">
            primitive behaviour parity vs Jev: choice 100% · score 100% · noul 100% — the
            Jev column describes the behaviour tydex clones when it is not publicly documented.
          </p>
        </Reveal>
      </Section>

      {/* ============ 06 · GET STARTED ============ */}
      <Section
        id="install"
        kicker="06 · get started"
        title="Live in five lines."
        lead={
          <>
            Install from PyPI, or run the container from GHCR. No runtime dependencies
            in the core — the async server needs two optional extras.
          </>
        }
      >
        <div className="grid gap-6 lg:grid-cols-2">
          <Reveal>
            <CodeBlock
              label="install · terminal"
              code={`$ ${CODE_INSTALL}`}
              hideToggle
              noPad
            />
          </Reveal>
          <Reveal delay={80}>
            <CodeBlock label="server · async FastAPI" code={CODE_SERVER} />
          </Reveal>
        </div>

        <div className="mt-16 grid gap-10 lg:grid-cols-2 lg:gap-0 lg:divide-x lg:divide-line">
          <div className="lg:pr-10">
            <Reveal>
              <p className="font-mono text-xs font-semibold tracking-widest text-mut uppercase">
                runs anywhere
              </p>
              <ul className="mt-5 space-y-3 font-mono text-sm text-ink">
                <li className="flex items-center gap-3">
                  <CheckIcon className="h-4 w-4 shrink-0 text-brand" />
                  pip install tydex
                </li>
                <li className="flex items-center gap-3">
                  <CheckIcon className="h-4 w-4 shrink-0 text-brand" />
                  docker pull ghcr.io/dracko000/tydex
                </li>
                <li className="flex items-center gap-3">
                  <CheckIcon className="h-4 w-4 shrink-0 text-brand" />
                  tydex providers in the CLI
                </li>
              </ul>
            </Reveal>
          </div>
          <div className="pt-10 lg:pl-10 lg:pt-0">
            <Reveal delay={80}>
              <p className="font-mono text-xs font-semibold tracking-widest text-mut uppercase">
                public artifacts
              </p>
              <div className="mt-5 flex flex-wrap gap-x-3 gap-y-2">
                <a href={LINKS.pypi} target="_blank" rel="noopener noreferrer" aria-label="PyPI version">
                  <img src="https://img.shields.io/pypi/v/tydex.svg" alt="PyPI version" className="h-6" />
                </a>
                <a href={LINKS.pypi} target="_blank" rel="noopener noreferrer" aria-label="Python versions">
                  <img src="https://img.shields.io/pypi/pyversions/tydex.svg" alt="Python versions" className="h-6" />
                </a>
                <a href="https://opensource.org/licenses/MIT" target="_blank" rel="noopener noreferrer" aria-label="License">
                  <img src="https://img.shields.io/pypi/l/tydex.svg" alt="License: MIT" className="h-6" />
                </a>
                <a href={LINKS.github} target="_blank" rel="noopener noreferrer" aria-label="CI status">
                  <img
                    src="https://img.shields.io/github/actions/workflow/status/Dracko000/tydex/ci.yml?branch=main&label=CI"
                    alt="CI"
                    className="h-6"
                  />
                </a>
                <a href={LINKS.releases} target="_blank" rel="noopener noreferrer" aria-label="Release">
                  <img
                    src="https://img.shields.io/github/v/release/Dracko000/tydex"
                    alt="GitHub release"
                    className="h-6"
                  />
                </a>
                <a href={LINKS.docs} target="_blank" rel="noopener noreferrer" aria-label="Docs">
                  <img
                    src="https://img.shields.io/badge/docs-live-2ea44f"
                    alt="Docs live"
                    className="h-6"
                  />
                </a>
              </div>
            </Reveal>
          </div>
        </div>
      </Section>

      {/* ============ CLIMAX CTA ============ */}
      <section className="pb-24 sm:pb-28">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Reveal>
            <div className="relative border-y border-line">
              <div className="grid-faint pointer-events-none absolute inset-0" aria-hidden />
              <div className="relative py-16 text-center sm:py-20">
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
                  <LiftedLink
                    href={LINKS.pypi}
                    target="_blank"
                    rel="noopener noreferrer"
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.98 }}
                    className="inline-flex h-12 cursor-pointer items-center gap-2 rounded-xl bg-flame px-5 text-base font-semibold text-white shadow-lg shadow-flame/25 transition-colors duration-200 hover:shadow-flame/40"
                  >
                    <CopyIcon className="h-5 w-5" />
                    pip install tydex
                  </LiftedLink>
                  <a
                    href={LINKS.github}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex h-12 cursor-pointer items-center gap-2 rounded-xl border border-line px-5 text-base font-semibold text-ink transition-colors duration-200 hover:text-brand"
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
      <footer className="border-t border-line">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
          <div className="grid gap-10 md:grid-cols-4">
            <div className="md:col-span-2">
              <span className="font-mono text-lg font-semibold text-ink">tydex</span>
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
                <li>
                  <a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href="#primitives">
                    Primitives
                  </a>
                </li>
                <li>
                  <a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href="#calibration">
                    Calibration
                  </a>
                </li>
                <li>
                  <a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href="#architecture">
                    Architecture
                  </a>
                </li>
                <li>
                  <a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href="#vs-jev">
                    vs Jev
                  </a>
                </li>
                <li>
                  <a className="cursor-pointer text-ink transition-colors duration-200 hover:text-brand" href="#install">
                    Install
                  </a>
                </li>
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