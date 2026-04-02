# OSOP Workflow Example — CAMEL Society of Mind

This directory contains a portable workflow definition for CAMEL's **Society of Mind** multi-agent pattern, written in [OSOP](https://github.com/osop-org/osop-spec) format.

## What is OSOP?

**OSOP** (Open Standard for Orchestration Protocols) is a YAML-based workflow standard that describes multi-step processes — including AI agent pipelines — in a portable, tool-agnostic format. Think of it as "OpenAPI for workflows."

- Any tool can read and render an `.osop` file
- Workflows become shareable, diffable, and version-controllable
- No vendor lock-in: the same workflow runs across different orchestration engines

## Files

| File | Description |
|------|-------------|
| `society-of-mind.osop` | CAMEL's role-playing multi-agent debate pattern — task specifier, assistant, user, and critic agents collaborating through structured dialogue |

## How to use

You can read the `.osop` file as plain YAML. To validate or visualize it:

```bash
# Validate the workflow
pip install osop
osop validate society-of-mind.osop

# Generate a visual report
npx osop-report society-of-mind.osop -o report.html
```

## Learn more

- [OSOP Spec](https://github.com/osop-org/osop-spec) — Full specification
- [OSOP Examples](https://github.com/osop-org/osop-examples) — 30+ workflow templates
- [CAMEL Documentation](https://docs.camel-ai.org/) — CAMEL framework docs
