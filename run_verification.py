"""
Verification Runner Script

This script runs verification metrics on generated literature survey reports
and saves the results to JSON files.

Usage:
    python run_verification.py --report workspace/report.md
    python run_verification.py --report workspace/report.md --output results.json
    python run_verification.py --all  # Verify all reports in workspace
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.logger import logger
from app.verification import EvidenceMatchMetric  # V1: TF-IDF + keyword matching
from app.verification import EvidenceMatchV2Metric  # V2: Embeddings-based
from app.verification import CitationAccuracyMetric, ClaimSupportMetric, ReportParser


class VerificationRunner:
    """
    Runs verification metrics on literature survey reports.
    """

    def __init__(self):
        self.metrics = [
            CitationAccuracyMetric(),
            ClaimSupportMetric(),
            EvidenceMatchMetric(),  # V1: TF-IDF + keyword matching (offline)
            EvidenceMatchV2Metric(),  # V2: Embeddings-based (better accuracy, requires API)
            # Future metrics will be added here:
            # HallucinationMetric(),
        ]

    async def verify_report(
        self, report_path: str, output_path: str = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Run all verification metrics on a report.

        Args:
            report_path: Path to the report file
            output_path: Path to save results JSON (optional)
            **kwargs: Additional parameters for metrics

        Returns:
            Dictionary containing all verification results
        """
        report_path = Path(report_path)

        if not report_path.exists():
            logger.error(f"Report file not found: {report_path}")
            raise FileNotFoundError(f"Report not found: {report_path}")

        logger.info(f"Starting verification for: {report_path.name}")
        logger.info(f"Running {len(self.metrics)} metrics...")

        # Parse report to get basic statistics
        parser = ReportParser(str(report_path))
        parser.parse()
        stats = parser.get_statistics()

        # Run all metrics
        results = {
            "report_path": str(report_path),
            "report_name": report_path.name,
            "verification_timestamp": datetime.now().isoformat(),
            "report_statistics": stats,
            "metrics": {},
            "overall_score": 0.0,
        }

        # Execute metrics sequentially (can be parallelized if needed)
        metric_scores = []
        for metric in self.metrics:
            logger.info(f"Calculating {metric.name}...")
            try:
                result = await metric.calculate(str(report_path), **kwargs)
                results["metrics"][metric.name] = result.to_dict()
                metric_scores.append(result.score)

                logger.info(
                    f"✓ {metric.name}: {result.score:.2%} "
                    f"({result.passed_checks}/{result.total_checks})"
                )
            except Exception as e:
                logger.error(f"Error calculating {metric.name}: {e}")
                results["metrics"][metric.name] = {"error": str(e), "score": 0.0}

        # Calculate overall score (average of all metrics)
        if metric_scores:
            results["overall_score"] = sum(metric_scores) / len(metric_scores)
            logger.info(f"\nOverall Verification Score: {results['overall_score']:.2%}")

        # Save results to JSON if output path specified
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"Results saved to: {output_path}")
        else:
            # Default output path: same name as report with .json extension
            default_output = (
                report_path.parent / f"{report_path.stem}_verification.json"
            )
            with open(default_output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"Results saved to: {default_output}")

        return results

    async def verify_all_reports(
        self, workspace_dir: str = "workspace", output_dir: str = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Verify all reports in a directory.

        Args:
            workspace_dir: Directory containing reports
            output_dir: Directory to save verification results
            **kwargs: Additional parameters for metrics

        Returns:
            List of verification results for all reports
        """
        workspace_path = Path(workspace_dir)

        if not workspace_path.exists():
            logger.error(f"Workspace directory not found: {workspace_dir}")
            raise FileNotFoundError(f"Workspace not found: {workspace_dir}")

        # Find all markdown and text files
        report_files = list(workspace_path.glob("*.md")) + list(
            workspace_path.glob("*.txt")
        )

        # Filter out example files
        report_files = [f for f in report_files if "example" not in f.name.lower()]

        if not report_files:
            logger.warning(f"No report files found in {workspace_dir}")
            return []

        logger.info(f"Found {len(report_files)} reports to verify")

        # Verify each report
        all_results = []
        for i, report_file in enumerate(report_files, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"Verifying report {i}/{len(report_files)}: {report_file.name}")
            logger.info(f"{'='*80}")

            try:
                # Determine output path
                if output_dir:
                    output_path = (
                        Path(output_dir) / f"{report_file.stem}_verification.json"
                    )
                else:
                    output_path = (
                        report_file.parent / f"{report_file.stem}_verification.json"
                    )

                result = await self.verify_report(
                    str(report_file), str(output_path), **kwargs
                )
                all_results.append(result)

            except Exception as e:
                logger.error(f"Failed to verify {report_file.name}: {e}")

        # Create summary
        if all_results:
            summary = self._create_summary(all_results)
            summary_path = Path(workspace_dir) / "verification_summary.json"

            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            logger.info(f"\n{'='*80}")
            logger.info(f"Verification Summary:")
            logger.info(f"  Total Reports: {summary['total_reports']}")
            logger.info(
                f"  Average Overall Score: {summary['average_overall_score']:.2%}"
            )
            logger.info(f"  Summary saved to: {summary_path}")
            logger.info(f"{'='*80}")

        return all_results

    def _create_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary of all verification results."""
        total_reports = len(results)
        overall_scores = [r["overall_score"] for r in results]

        summary = {
            "total_reports": total_reports,
            "average_overall_score": (
                sum(overall_scores) / total_reports if overall_scores else 0
            ),
            "timestamp": datetime.now().isoformat(),
            "metric_averages": {},
            "reports": [],
        }

        # Calculate average for each metric
        metric_names = set()
        for result in results:
            metric_names.update(result["metrics"].keys())

        for metric_name in metric_names:
            scores = [
                r["metrics"][metric_name]["score"]
                for r in results
                if metric_name in r["metrics"] and "score" in r["metrics"][metric_name]
            ]
            if scores:
                summary["metric_averages"][metric_name] = sum(scores) / len(scores)

        # Add report summaries
        for result in results:
            summary["reports"].append(
                {
                    "name": result["report_name"],
                    "overall_score": result["overall_score"],
                    "total_citations": result["report_statistics"].get(
                        "total_citations", 0
                    ),
                    "verification_timestamp": result["verification_timestamp"],
                }
            )

        return summary


async def main():
    """Main entry point for verification runner."""
    parser = argparse.ArgumentParser(
        description="Run verification metrics on literature survey reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify a single report
  python run_verification.py --report workspace/GLP-1_Agonists_Diabetes_Survey.md

  # Verify with custom output path
  python run_verification.py --report workspace/report.md --output results/verification.json

  # Verify all reports in workspace
  python run_verification.py --all

  # Verify all reports with custom workspace
  python run_verification.py --all --workspace my_reports/

  # Skip URL accessibility checks (faster)
  python run_verification.py --report workspace/report.md --no-check-urls
        """,
    )

    parser.add_argument(
        "--report", type=str, help="Path to a specific report file to verify"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Path to save verification results JSON (default: same directory as report)",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Verify all reports in the workspace directory",
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default="workspace",
        help="Workspace directory containing reports (default: workspace)",
    )

    parser.add_argument(
        "--no-check-urls",
        action="store_true",
        help="Skip URL accessibility checks (faster but less thorough)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout for URL checks in seconds (default: 10)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.report:
        parser.error("Either --report or --all must be specified")

    if args.all and args.report:
        parser.error("Cannot specify both --report and --all")

    # Set up kwargs for metrics
    metric_kwargs = {
        "check_accessibility": not args.no_check_urls,
        "timeout": args.timeout,
    }

    # Create runner
    runner = VerificationRunner()

    # Run verification
    try:
        if args.all:
            await runner.verify_all_reports(
                workspace_dir=args.workspace, **metric_kwargs
            )
        else:
            await runner.verify_report(
                report_path=args.report, output_path=args.output, **metric_kwargs
            )

        logger.info("\n✓ Verification completed successfully!")

    except Exception as e:
        logger.error(f"\n✗ Verification failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
