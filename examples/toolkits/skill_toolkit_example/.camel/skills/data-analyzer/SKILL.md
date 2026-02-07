---
name: data-analyzer
description: Analyze datasets and extract insights. Use when user needs to understand data patterns, statistics, or trends.
---

# Data Analyzer

Analyze data and provide statistical insights.

## Workflow

1. Load and inspect the data structure
2. Compute basic statistics (mean, median, std, min, max)
3. Identify patterns and anomalies
4. Summarize key findings

## Output Format

Provide analysis in this structure:

```
## Data Overview
- Total records: X
- Columns: [list]

## Key Statistics
| Metric | Value |
|--------|-------|
| ...    | ...   |

## Insights
- Finding 1
- Finding 2
```

## Guidelines

- Always validate data types before analysis
- Handle missing values explicitly
- Report confidence levels for statistical claims
