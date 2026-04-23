# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""
Example of using WebJudgeVisionEvaluator with DOM-based evaluation.

This example demonstrates:
1. Loading a browser automation session
2. Configuring WebJudgeVisionEvaluator with DOM snapshots (not screenshots)
3. Running evaluate_session to assess task completion using DOM content
4. Analyzing and displaying evaluation results with key points and evidence

DOM-Based Evaluation:
- Uses cleaned DOM snapshots instead of screenshots
- More lightweight and efficient for text-based analysis
- Provides structured HTML content for precise evaluation
- Ideal for web navigation and form-filling tasks
"""
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from camel.evaluators.webjudge import (
    WebJudgeVisionConfig,
    WebJudgeVisionEvaluator,
)
from camel.types import ModelPlatformType, ModelType


class WebJudgeSessionEvaluator:
    """Wrapper for easy evaluation of browser automation sessions."""

    def __init__(
        self,
        model_platform: ModelPlatformType = ModelPlatformType.AZURE,
        model_type: ModelType = ModelType.GPT_5_2,
        persist_cleaned_dom: bool = True,
    ):
        """Initialize the evaluator with DOM-based configuration.
        
        Uses DOM snapshots for evaluation instead of screenshots.
        This provides text-based, structured HTML content for precise task assessment.
        
        Args:
            model_platform: Model platform to use (e.g., OpenAI, Anthropic)
            model_type: Model type to use (e.g., GPT-4)
            persist_cleaned_dom: Whether to save cleaned DOM snapshots for debugging
        """
        config = WebJudgeVisionConfig(
            model_platform=model_platform,
            model_type=model_type,
            vision_type="dom",  # Use DOM snapshots (structured HTML)
            persist_cleaned_dom=persist_cleaned_dom,
            step_timeout=360.0,
            tool_execution_timeout=360.0,
            evidence_score_threshold=3,
            min_images_for_outcome=3,
            max_images_for_outcome=16,
        )
        self.evaluator = WebJudgeVisionEvaluator(config=config)

    def evaluate_from_path(
        self,
        session_dir: str,
        task: str,
        website: str,
        agent_response: str = "Task completed.",
    ) -> dict:
        """Evaluate a session and return structured results.
        
        Args:
            session_dir: Path to the session directory
            task: The task description that was performed
            website: The website name (e.g., "Google Flights")
            agent_response: The agent's final response (optional)
            
        Returns:
            Dictionary with evaluation results
        """
        session_path = Path(session_dir).expanduser().resolve()

        if not session_path.exists():
            raise FileNotFoundError(f"Session directory not found: {session_dir}")

        print(f"\n{'=' * 80}")
        print("🔍 VISION-WEBJUDGE SESSION EVALUATION")
        print(f"{'=' * 80}")
        print(f"📂 Session: {session_path.name}")
        print(f"🌐 Website: {website}")
        print(f"📋 Task: {task[:100]}..." if len(task) > 100 else f"📋 Task: {task}")
        print()

        # Run evaluation
        result = self.evaluator.evaluate_session(
            task=task,
            session_dir=session_path,
            agent_response=agent_response,
            website=website,
        )

        # Display results
        self._display_results(result)

        # Return structured results
        return {
            "success": result.success,
            "reasoning": result.reasoning,
            "suggestions": result.suggestions,
            "key_points": result.key_points,
            "evidence_count": len(result.evidence),
            "execution_time": result.execution_time,
            "token_usage": result.token_usage,
            "debug_path": result.debug_path,
        }

    def _display_results(self, result) -> None:
        """Display evaluation results in a formatted way."""
        print(f"{'=' * 80}")
        print("📊 EVALUATION RESULTS")
        print(f"{'=' * 80}")

        # Success status
        status_icon = "✅" if result.success else "❌"
        print(f"{status_icon} Task Success: {result.success}")
        print()

        # Reasoning
        print("💭 Reasoning:")
        print(f"   {result.reasoning}")
        print()

        # Suggestions
        if result.suggestions and result.suggestions != result.reasoning:
            print("💡 Suggestions:")
            print(f"   {result.suggestions}")
            print()

        # Key Points
        print(f"🔑 Key Points Identified ({len(result.key_points)}):")
        for i, kp in enumerate(result.key_points, 1):
            print(f"   {i}. {kp}")
        print()

        # Evidence
        print(f"📸 Evidence Frames Selected ({len(result.evidence)}):")
        for evidence in result.evidence:
            score_str = f"(score: {evidence.score})" if evidence.score else ""
            print(
                f"   - {evidence.frame_id}: {evidence.action} {score_str}"
            )
        print()

        # Performance metrics
        print("⏱️  Performance:")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        print()

        # Token usage
        if result.token_usage:
            print("🔢 Token Usage:")
            print(
                f"   Prompt: {result.token_usage.get('prompt', 0)}"
            )
            print(
                f"   Completion: {result.token_usage.get('completion', 0)}"
            )
            print(
                f"   Total: {result.token_usage.get('total', 0)}"
            )
            print()

        # Debug info
        print("🔧 Debug Information:")
        print(f"   Debug JSON: {result.debug_path}")
        print()


def example_google_flights() -> None:
    """Example: Evaluate a Google Flights session."""
    # Path to the session directory
    session_dir = Path(
        "examples/evaluators/webjudge/"
        "task_navi_bench_google_flights_airline_search_session"
    )

    # Task description
    task = (
        "Search for Economy class flights from VIE to MCO for 2 adult passengers "
        "for the date range July 28th-31st, 2026. "
        "What is the total price for the cheapest departure and return flight?"
    )

    # Website name
    website = "Google Flights"

    # Agent's response (could be extracted from session logs)
    agent_response = (
        "I have successfully searched for Economy flights from Vienna (VIE) to Orlando (MCO) "
        "for 2 adults from July 28-31, 2026. The search results are displayed on the page."
    )

    # Create evaluator
    evaluator = WebJudgeSessionEvaluator()

    # Evaluate the session
    try:
        results = evaluator.evaluate_from_path(
            session_dir=str(session_dir),
            task=task,
            website=website,
            agent_response=agent_response,
        )

        # Save results to file
        output_file = session_dir / "vision_webjudge_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Results saved to: {output_file}")

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print(f"   Expected session at: {session_dir.resolve()}")
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()




def main() -> None:
    """Run DOM-based evaluation examples."""
    print("\n" + "=" * 80)
    print("WebJudgeVisionEvaluator - DOM-Based Evaluation Examples")
    print("=" * 80)
    print("\nDOM Evaluation Features:")
    print("  • Uses cleaned DOM snapshots (structured HTML content)")
    print("  • Lightweight and efficient for text-based analysis")
    print("  • Perfect for form-filling and navigation tasks")
    print("  • Provides structured content for precise evaluation")
    print()

    # Example 1: Basic Google Flights evaluation with DOM
    print("\nBasic Google Flights Session Evaluation (DOM-based)")
    print("-" * 80)
    example_google_flights()
    print("\n" + "=" * 80)
    print("✅ DOM-Based Evaluation Examples Completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
