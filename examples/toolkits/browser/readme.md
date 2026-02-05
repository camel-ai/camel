# Introduction
This is folder for the browser agent expriments.
- browser_example: non-skill version with pure toolkit agent
- browser_skills_example: skill version with toolkit agent + browser skills

For now we have benchmarks for:
- [Webvoayer](https://github.com/MinorJerry/WebVoyager/blob/main/data/WebVoyager_data.jsonl): google flights, coursera

On going dataset:
- [navi-bench](https://huggingface.co/datasets/yutori-ai/navi-bench)

# Running Experiments
When you run the experiments make sure following settings are correct:
1. Setup the api keys in the .env file.
2. browser_example has the non-skill version with pure toolkit agent and browser_skills_example has the skill version. Make sure you run the correct one.
3. In modeling.py, make sure the DEFAULT_MODEL_PLATFORM and DEFAULT_MODEL_TYPE are the correct ones you want to use.
4. get the submodules if you need to run the navi-bench related experiments:
    ```bash
    git submodule update --init examples/toolkits/browser/navi-bench
    ```
  Install the navi-bench package with uv:
    ```bash
    cd examples/toolkits/browser/navi-bench
    uv pip install .
    ```
# Commands to run the experiments

## WebVoyager
python -m examples.toolkits.browser.browser_skills_example.cli.run_webvoyager_tasks --jsonl examples/toolkits/browser/data/WebVoyager_data.jsonl --skills-root examples/toolkits/browser/browser_skills_example/skills_store --start 301 --max-tasks 42

## Navi-bench
### Without skills version
```bash
python -m examples.toolkits.browser.browser_example.cli.run_navi_bench_tasks --jsonl examples\toolkits\browser\data\navi_bench_data.jsonl --domain apartments
```


### With skills version
```bash
python -m examples.toolkits.browser.browser_skills_example.cli.run_navi_bench_case --jsonl examples\toolkits\browser\data\navi_bench_data.jsonl --skills-root examples\toolkits\browser\browser_skills_example\skills_store --task-id navi_bench/apartments/ny_multi_region_search/12


python -m examples.toolkits.browser.browser_skills_example.cli.run_navi_bench_tasks --jsonl examples\toolkits\browser\data\navi_bench_data.jsonl --skills-root examples/toolkits/browser/browser_skills_example/skills_store --start 0 --max-tasks 10

python -m examples.toolkits.browser.browser_skills_example.cli.run_navi_bench_tasks --jsonl examples\toolkits\browser\data\navi_bench_data.jsonl --skills-root examples/toolkits/browser/browser_skills_example/skills_store --domain apartments
```