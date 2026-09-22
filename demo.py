import os

from tydex import (
    CalibrationSystem,
    MockBackend,
    OllamaBackend,
    OpenAIBackend,
    Recorder,
    RequiresHuman,
    RoutedTydex,
    Tier,
    Tydex,
    calibrate_temperature,
)

state = {
    "ticket": "#4821",
    "priority": "high",
    "escalated": True,
    "customer_plan": "enterprise",
    "sla_window_hours": 2,
}


def run_with(tdex: Tydex, label: str) -> None:
    print(f"=== {label} ===")

    c = tdex.choice(
        state,
        ["refund", "replace", "escalate_support", "wait_and_see"],
        question="What is the best action for this support ticket?",
    )
    print(f"choice      -> {c.choice}  (conf {c.confidence:.2f})")
    for opt, p in c.probabilities.items():
        print(f"               {opt:<16}{p:.3f}")

    s = tdex.score(state, ["critical", "high", "medium", "low"], question="How urgent is this ticket?")
    print(f"score       -> {s.score}  (conf {s.confidence:.2f})")

    n = tdex.noul(state, "This ticket must be handled within the SLA window.")
    print(f"noul        -> P(true) = {n.probability:.3f}  (bool: {n.bool_value}, conf {n.confidence:.2f})")
    print()


def demo_calibration() -> None:
    samples = [
        ({"item": "a"}, ["refund", "replace"], "Action?", "refund"),
        ({"item": "b"}, ["refund", "replace"], "Action?", "refund"),
        ({"item": "c"}, ["refund", "replace"], "Action?", "replace"),
        ({"item": "d"}, ["refund", "replace"], "Action?", "replace"),
    ]
    model = MockBackend({"0": 0.95, "1": 0.05, "Yes": 0.7, "No": 0.3})
    result = calibrate_temperature(Tydex(model), samples)
    print("=== Calibration (Mock) ===")
    print(f"baseline ECE {result.baseline.ece:.3f}  confidence {result.baseline.mean_confidence:.2f}  acc {result.baseline.accuracy:.2f}")
    print(f"best T={result.temperature:.1f}  -> ECE {result.metrics.ece:.3f}  confidence {result.metrics.mean_confidence:.2f}")


def demo_escalation() -> None:
    local_weak = MockBackend({"0": 0.55, "1": 0.45, "Yes": 0.6, "No": 0.4})
    frontier_strong = MockBackend({"0": 0.92, "1": 0.08, "Yes": 0.88, "No": 0.12})

    routed = RoutedTydex(
        [
            Tier(Tydex(local_weak), threshold=0.8, label="local-llama", cost=0.1),
            Tier(Tydex(frontier_strong), threshold=None, label="frontier-gpt4o", cost=1.0),
        ],
        on_escalation=lambda tier, conf, thr, cost: print(f"  [escalate] {tier} conf {conf:.2f} < {thr:.2f} (cost so far {cost:.2f})"),
    )

    print("=== Escalation by confidence ===")
    r = routed.choice({"ticket": "#9"}, ["refund", "replace"], question="Action?")
    print(f"choice  -> {r.result.choice}  conf {r.confidence:.2f}  via {r.tier}  (route {r.escalations}, cost {r.total_cost:.2f})")
    m = routed.score({"ticket": "#9"}, ["urgent", "normal"], question="Urgency?")
    print(f"score   -> {m.result.score}  conf {m.confidence:.2f}  via {m.tier}  (route {m.escalations}, cost {m.total_cost:.2f})")

    human_routed = RoutedTydex(
        [
            Tier(Tydex(local_weak), threshold=0.9, label="local-llama", cost=0.1),
            Tier(action="human", label="human", cost=10.0),
        ]
    )
    try:
        human_routed.noul({"ticket": "#9"}, "Refund the customer.")
    except RequiresHuman as exc:
        print(f"noul    -> {exc}  (request keys: {sorted(exc.request)})")


def demo_calibration_system() -> None:
    system = CalibrationSystem(Recorder("tydex-feedback.jsonl"), min_samples=4).fit()
    if not system.meta:
        print("=== CalibrationSystem ===  (no labeled data yet, run bench.py first)")
        return
    print("=== CalibrationSystem (fit dari log nyata) ===")
    for prim, meta in system.meta.items():
        print(f"  {prim:<7} n={meta['n']:>3} acc={meta['accuracy']:.2f} "
              f"ECE {meta['ece_before']:.3f} -> {meta['ece_after_calibrator']:.3f}  "
              f"T={meta['temperature']:.1f}")
    calibrated = system.apply_to(Tydex(MockBackend(), model="mock"))
    r = calibrated.choice(state, ["refund", "replace", "wait"], question="Best action?")
    print(f"  applied -> choice {r.choice}, conf {r.confidence:.2f} ({r.source})")
    system.save()


if __name__ == "__main__":
    run_with(Tydex(MockBackend()), "Mock backend (no API key needed)")
    demo_calibration()
    demo_escalation()
    demo_calibration_system()

    try:
        run_with(Tydex(OllamaBackend(model="llama3.1:8b")), "Ollama local")
    except Exception as exc:
        print(f"Ollama skipped: {exc}")

    if os.environ.get("OPENAI_API_KEY"):
        run_with(
            Tydex(OpenAIBackend(model="gpt-4o-mini")),
            "OpenAI (logprobs path)",
        )
    else:
        print("Set OPENAI_API_KEY to also test the OpenAI backend.")