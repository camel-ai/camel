# Introduction
This is folder for the skill-based browser agent expriments.

For now we have benchmarks for:
- [Webvoayer](https://github.com/MinorJerry/WebVoyager/blob/main/data/WebVoyager_data.jsonl): google flights, coursera

On going dataset:
- [navi-bench](https://huggingface.co/datasets/yutori-ai/navi-bench)

# Running Experiments
When you run the experiments make sure following settings are correct:
1. Setup the api keys in the .env file.
2. browser_example has the non-skill version with pure toolkit agent and browser_skills_example has the skill version. Make sure you run the correct one.
3. In modeling.py, make sure the DEFAULT_MODEL_PLATFORM and DEFAULT_MODEL_TYPE are the correct ones you want to use.

# Commands to run the experiments
python run_webvoyager_tasks.py --jsonl WebVoyager_data.jsonl --skills-root browser_skills --start 301 --max-tasks 42