from pathlib import Path
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


BACKEND_DIR = Path(__file__).resolve().parents[1]

CHECKS = [
    ("compileall", ["-m", "compileall", "app", "scripts"]),
    ("openapi_contract", ["scripts/test_openapi_contract.py"]),
    ("guardrail_and_prompt", ["scripts/test_guardrail_and_prompt.py"]),
    ("evaluation_edge_cases", ["scripts/test_evaluation_edge_cases.py"]),
    ("generate_and_evaluate_api", ["scripts/test_generate_and_evaluate_api.py"]),
]


def run_check(name: str, args: list[str]) -> tuple[bool, float]:
    started_at = time.perf_counter()
    print(f"\n=== {name} ===")
    result = subprocess.run(
        [sys.executable, *args],
        cwd=BACKEND_DIR,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = round(time.perf_counter() - started_at, 2)
    ok = result.returncode == 0
    print(f"{name}: {'PASS' if ok else 'FAIL'} ({elapsed}s)")
    return ok, elapsed


def main() -> None:
    results: list[dict] = []
    for name, args in CHECKS:
        ok, elapsed = run_check(name, args)
        results.append({"name": name, "ok": ok, "elapsed_seconds": elapsed})
        if not ok:
            print("\nP2/P3 smoke test failed.")
            print({"results": results})
            raise SystemExit(1)

    total = round(sum(item["elapsed_seconds"] for item in results), 2)
    print("\nP2/P3 smoke test passed.")
    print({"check_count": len(results), "total_elapsed_seconds": total, "results": results})


if __name__ == "__main__":
    main()
