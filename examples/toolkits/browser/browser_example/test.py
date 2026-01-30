from camel.evaluators.webjudge import (
    WebJudgeVisionConfig,
    WebJudgeVisionEvaluator,
)
from modeling import DEFAULT_MODEL_PLATFORM, DEFAULT_MODEL_TYPE
from pathlib import Path
from typing import Any, Dict, List

import dotenv
dotenv.load_dotenv()

class WebJudgeTaskVerifier:
    """WebJudge-based verifier using session evidence (vision-only)."""

    def __init__(
        self,
        *,
        vision_config: WebJudgeVisionConfig | None = None,
    ):
        resolved_config = vision_config or WebJudgeVisionConfig(
            model_platform=DEFAULT_MODEL_PLATFORM,
            model_type=DEFAULT_MODEL_TYPE,
        )
        self.vision_evaluator = WebJudgeVisionEvaluator(config=resolved_config)

    def verify_task(
        self,
        task_description: str,
        agent_response: str,
        *,
        session_dir: Path | None = None,
        website: str | None = None,
    ) -> Dict[str, Any]:
        if session_dir is None:
            return {
                "success": False,
                "reasoning": "WebJudge verifier requires session_dir evidence",
                "suggestions": "Re-run with session logging enabled and pass session_dir to the verifier.",
            }
        return self.vision_evaluator.evaluate_session(
            task=task_description,
            session_dir=session_dir,
            agent_response=agent_response,
            website=website,
        )
    
verifier = WebJudgeTaskVerifier()
task_description = "Search for a beginner-level online course about Python programming, suitable for someone who has no programming experience on Coursera."
agent_response = """Here is a highly recommended beginner-level online course about Python programming on Coursera, suitable for someone with no programming experience:\n\n---\n\n### Course Title:\n**Programming for Everybody (Getting Started with Python)**\n\n### Offered by:\nUniversity of Michigan\n\n### Instructor:\n- Charles Russell Severance (Dr. Chuck)\n\n### Level:\n- Beginner level\n- No prior experience required\n\n### Language:\n- Taught in French (AI Dubbing) and available in 30 languages\n\n### Duration & Schedule:\n- Approx. 2 weeks at 10 hours per week (learn at your own pace)\n- Flexible schedule\n\n### What you'll learn:\n- Install Python and write your first program\n- Describe the basics of the Python programming language\n- Use variables to store, retrieve, and calculate information\n- Utilize core programming tools such as functions and loops\n\n### Syllabus (Modules):\n1. Chapter One - Why We Program\n2. Installing Python\n3. Chapter One: Why We Program (continued)\n4. Chapter Two: Variables and Expressions\n5. Chapter Three: Conditional Code\n6. Chapter Four: Functions\n7. Chapter Five: Loops and Iteration\n\n### Skills you'll gain:\n- Computational Thinking\n- Python Programming\n- Software Installation\n- Development Environment\n- Programming Principles\n- Computer Programming\n\n### Certificate:\n- Shareable certificate upon completion (can be added to LinkedIn)\n\n### Ratings:\n- 4.8 out of 5 stars (over 232,000 reviews)\n- 3,492,659 learners already enrolled\n\n### Course Description:\nThis course aims to teach everyone the basics of programming computers using Python. It covers the basics of how one constructs a program from a series of simple instructions in Python. The course has no pre-requisites and avoids all but the simplest mathematics. Anyone with moderate computer experience should be able to master the materials in this course.\n\n---\n\n**Link to course:**  \n[Programming for Everybody (Getting Started with Python) | Coursera](https://www.coursera.org/learn/python)\n\nThis course is an excellent starting point for absolute beginners and is part of the \"Python for Everybody\" specialization, but you can take it as a standalone course as well.\n\n##TASK_DONE##"""
session_dir = r"C:\Users\moizh\workspace\camel\examples\toolkits\session_logs\session_20260121_021331\task_Coursera--1_attempt_1"
website = "coursera"
verification = verifier.verify_task(
    task_description,
    agent_response,
    session_dir=session_dir,
    website=website,
)
