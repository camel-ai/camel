# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import argparse
import json
import logging
import os
from datetime import datetime

from camel.logger import get_logger

# Try to import tqdm for evaluation progress display
try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    logging.warning(
        "Note: tqdm is not installed, progress bar will not be displayed. "
        "You can install it using 'pip install tqdm'."
    )

from camel.benchmarks.bfcl import run_bfcl_benchmark

logger = get_logger(__name__)


if __name__ == "__main__":
    # set up logging
    logger.setLevel(logging.INFO)

    parser = argparse.ArgumentParser(
        description="Run BFCL benchmark on a model."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="Model to evaluate (default: gpt-4o)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="simple",
        choices=[
            "simple",
            "multiple",
            "parallel",
            "parallel_multiple",
            "irrelevance",
            "java",
            "javascript",
            "rest",
        ],
        help="Category of function calls to evaluate (default: simple)",
    )
    parser.add_argument(
        "--data_dir",
        type=str,
        default="data/bfcl",
        help="Directory to store dataset (default: data/bfcl)",
    )
    parser.add_argument(
        "--save_to",
        type=str,
        default="results/bfcl",
        help="Directory to save results (default: results/bfcl)",
    )
    parser.add_argument(
        "--subset",
        type=int,
        default=None,
        help="Number of samples to evaluate (default: all)",
    )
    parser.add_argument(
        "--api_key",
        type=str,
        default=None,
        help="API key for the model",
    )
    parser.add_argument(
        "--base_url",
        type=str,
        default=None,
        help="Base URL for API requests",
    )
    parser.add_argument(
        "--model_platform",
        type=str,
        default="openai",
        help="Platform of the model (default: openai)",
    )
    parser.add_argument(
        "--run_all",
        action="store_true",
        help="Run benchmark on all categories",
    )
    parser.add_argument(
        "--force_download",
        action="store_true",
        help="Force download dataset even if it exists",
    )

    args = parser.parse_args()

    # If run_all flag is set, run all categories
    if args.run_all:
        logger.info("Running benchmark on all categories...")

        # Store all category results
        all_results = {}
        total_correct = 0
        total_samples = 0

        # Define categories to test for run_all except rest because rest does
        # not have an official possible answer
        categories_to_run = [
            "simple",
            "multiple",
            "parallel",
            "parallel_multiple",
            "irrelevance",
            "java",
            "javascript",
        ]

        # Create iterator with progress bar if available
        if TQDM_AVAILABLE:
            # use position parameter to keep the progress bar on a separate
            # line
            categories_iter = tqdm(
                categories_to_run,
                desc="Testing categories",
                position=0,
                leave=True,
            )
        else:
            categories_iter = categories_to_run

        # Run each category test
        for category in categories_iter:
            logger.info(f"\n{'='*40}")
            logger.info(f"Testing category: {category}")
            logger.info(f"{'='*40}")

            # Set different save path for each category
            save_path = os.path.join(args.save_to, f"{category}")

            try:
                benchmark = run_bfcl_benchmark(
                    model_name=args.model,
                    category=category,
                    data_dir=args.data_dir,
                    save_to=save_path,
                    subset=args.subset,
                    api_key=args.api_key,
                    base_url=args.base_url,
                    model_platform=args.model_platform,
                    force_download=args.force_download,
                )

                # Calculate and save results
                if benchmark and benchmark.results:
                    results = benchmark.results
                    correct = sum(1 for r in results if r["result"])
                    total = len(results)
                    accuracy = correct / total if total > 0 else 0

                    all_results[category] = {
                        "accuracy": accuracy,
                        "correct": correct,
                        "total": total,
                    }

                    total_correct += correct
                    total_samples += total
                else:
                    logger.warning(f"BFCL {category}: No results to evaluate")
                    all_results[category] = {
                        "accuracy": 0,
                        "correct": 0,
                        "total": 0,
                    }
            except Exception as e:
                logger.error(f"Error running {category} category: {e}")
                all_results[category] = {
                    "accuracy": 0,
                    "correct": 0,
                    "total": 0,
                    "error": str(e),
                }

        # Calculate overall accuracy
        overall_accuracy = (
            total_correct / total_samples if total_samples > 0 else 0
        )

        # Log summary
        logger.info("\n" + "=" * 50)
        logger.info("BFCL Benchmark Summary")
        logger.info("=" * 50)
        logger.info(
            f"Overall accuracy: {overall_accuracy:.4f} "
            f"({total_correct}/{total_samples})"
        )
        logger.info("\nCategory accuracies:")

        # Create table format output
        logger.info(
            f"{'Category':<20} {'Accuracy':<10} {'Correct':<10} {'Total':<10}"
        )
        logger.info("-" * 50)

        for category, result in all_results.items():
            accuracy = result["accuracy"]
            correct = result["correct"]
            total = result["total"]
            logger.info(
                f"{category:<20} {accuracy:.4f}     {correct:<10} {total:<10}"
            )

        # Save summary results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_path = os.path.join(
            args.save_to,
            f"bfcl_summary_{args.model}_{timestamp}.json",
        )
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            summary = {
                "overall": {
                    "accuracy": overall_accuracy,
                    "correct": total_correct,
                    "total": total_samples,
                },
                "categories": all_results,
            }
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"\nSummary results saved to: {summary_path}")
    else:
        # Run a single category
        run_bfcl_benchmark(
            model_name=args.model,
            category=args.category,
            data_dir=args.data_dir,
            save_to=args.save_to,
            subset=args.subset,
            api_key=args.api_key,
            base_url=args.base_url,
            model_platform=args.model_platform,
            force_download=args.force_download,
        )
