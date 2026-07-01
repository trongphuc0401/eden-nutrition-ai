from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.research_rule_service import ResearchRuleService


def main() -> None:
    preview = ResearchRuleService().preview_rules()
    print(preview)


if __name__ == "__main__":
    main()
