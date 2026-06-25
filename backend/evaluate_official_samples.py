from pathlib import Path
import argparse

from app.routers.convert import OFFICIAL_DEMO_SAMPLES
from app.services.official_sample_evaluator import OfficialSampleEvaluator, acceptance_passed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate official Word/JATS sample pairs."
    )
    parser.add_argument(
        "--output",
        default="../docs/官方样例对比报告.md",
        help="Markdown report path",
    )
    parser.add_argument("--profile", default="default", help="Journal profile name")
    parser.add_argument("--average-floor", type=float, default=94.0)
    parser.add_argument("--minimum-floor", type=int, default=90)
    parser.add_argument("--schema-floor", type=float, default=1.0)
    args = parser.parse_args()

    samples = [
        sample
        for sample in OFFICIAL_DEMO_SAMPLES
        if Path(sample["docx"]).is_file() and Path(sample["xml"]).is_file()
    ]
    evaluator = OfficialSampleEvaluator(args.profile)
    results, summary = evaluator.evaluate(samples)
    output = evaluator.write_markdown(args.output, results, summary)
    print(f"samples={summary['sample_count']}")
    print(f"average_similarity={summary['average_similarity']}")
    print(f"minimum_similarity={summary['minimum_similarity']}")
    print(f"schema_valid_rate={summary['schema_valid_rate']:.4f}")
    passed = acceptance_passed(
        summary,
        average_floor=args.average_floor,
        minimum_floor=args.minimum_floor,
        schema_floor=args.schema_floor,
    )
    print(f"acceptance_passed={str(passed).lower()}")
    print(f"report={output.resolve()}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
