export type Benchmark = {
  id: string;
  name: string;
  before: number;
  after: number;
  temp: string;
  samples: number;
  accuracy: number;
};

export const BENCHMARKS: Benchmark[] = [
  { id: "choice", name: "choice", before: 0.35, after: 0.023, temp: "2.7", samples: 24, accuracy: 0.58 },
  { id: "score", name: "score", before: 0.313, after: 0.057, temp: "2.1", samples: 15, accuracy: 0.6 },
  { id: "noul", name: "noul", before: 0.161, after: 0.158, temp: "1.4", samples: 21, accuracy: 0.71 },
];

export const STATS = [
  { value: 91, suffix: "", label: "unit tests green" },
  { value: 60, suffix: "", label: "labeled tickets in the dataset" },
  { value: 3, suffix: "", label: "decision primitives" },
  { value: 9, suffix: "", label: "provider plugins" },
];

export const PROVIDERS = [
  "auto",
  "openai",
  "openai_compatible_cloud",
  "openai_compatible_local",
  "anthropic",
  "ollama",
  "mock",
];

export const ENDPOINTS = [
  { method: "GET", path: "/health", note: "liveness probe" },
  { method: "GET", path: "/calibration", note: "ECE + fitted temperature" },
  { method: "GET", path: "/suggest", note: "label suggestions" },
  { method: "POST", path: "/evaluate", note: "run a decision" },
  { method: "POST", path: "/label", note: "feedback → re-calibrate" },
  { method: "POST", path: "/refit", note: "re-fit calibration" },
];

export const CODE_CHOICE = `from tydex import Tydex
from tydex.backends import MockBackend

tdex = Tydex(MockBackend())

result = tdex.choice(
    state="Cart checkout returned HTTP 503",
    options=["Retry", "Degrade", "Escalate"],
    question="Which action keeps the cart safe?",
)
print(result)`;

export const CODE_CHOICE_OUT = `ChoiceResult(
  choice="Escalate",
  probabilities={
    "Retry":    0.10,
    "Degrade":  0.22,
    "Escalate": 0.68,
  },
  confidence=0.68,
  source="self",
)`;

export const CODE_SCORE = `result = tdex.score(
    state="CPU 97%, p95 latency 12s",
    levels=["OK", "Degraded", "Critical"],
    question="Service health level",
)
# ScoreResult(score="Critical", confidence=0.81, source="self")`;

export const CODE_NOUL = `result = tdex.noul(
    state="Refund was applied twice",
    statement="Ledger is neutral on this payment",
)
# NoulResult(probability=0.84, confidence=0.84, source="self")`;

export const CODE_INSTALL = `pip install tydex`;

export const CODE_SERVER = `from tydex import run
from tydex.backends import OpenAIBackend

run(
    backend=OpenAIBackend(api_key=os.environ["OPENAI_API_KEY"]),
    api_key="…",          # clients must send X-API-Key
    cors=True,
)
# FastAPI on http://127.0.0.1:8000  (OpenAPI: /docs)`;

export const LINKS = {
  github: "https://github.com/Dracko000/tydex",
  pypi: "https://pypi.org/project/tydex/",
  docs: "https://dracko000.github.io/tydex/docs/",
  ghcr: "https://github.com/Dracko000/tydex/pkgs/container/tydex",
  releases: "https://github.com/Dracko000/tydex/releases",
  changelog: "https://github.com/Dracko000/tydex/blob/main/CHANGELOG.md",
};