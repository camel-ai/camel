# TraceRoot Usage Guide

TraceRoot is an open-source LLM debugging platform that correlates logging and tracing. This guide covers how to use TraceRoot with the CAMEL project.


## Table of Contents

- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [Self-Hosted Deployment](#self-hosted-deployment)
- [Related Links](#related-links)

## Quick Start

### 1. Install Dependencies

```bash
uv pip install ".[dev_tools]"
```

### 2. Environment Variables Configuration

Before using TraceRoot, set the following environment variables:

```bash
# Enable TraceRoot for debugging
export TRACEROOT_ENABLED="true"
python examples/debug/traceroot_example.py
# or
python examples/debug/eigent.py
```

Some of the configuration options specified in the `.traceroot-config.yaml` file.

And then if you import `import traceroot` in your Python code, the traceroot functionality will be automatically enabled.

### 3. Self-Hosted Deployment

And for now you need to [reach out to us](https://traceroot.ai/) to get necessary details for the TraceRoot setup. The open source version will be available soon.


## Related Links

- [TraceRoot Documentation](https://docs.traceroot.ai/)
- [TraceRoot LinkedIn](https://www.linkedin.com/company/traceroot-ai)
