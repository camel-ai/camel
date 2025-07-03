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
# Enable TraceRoot debugging
export TRACEROOT_ENABLED="true"
python camel/examples/debug/traceroot_example.py
```

### 3. Self-Hosted Deployment

And for now you need to [reach out to us](https://traceroot.ai/) to get necessary details for the TraceRoot setup. The open source version will be available soon.


## Related Links

- [TraceRoot Documentation](https://docs.traceroot.ai/)
- [TraceRoot LinkedIn](https://www.linkedin.com/company/traceroot-ai)
