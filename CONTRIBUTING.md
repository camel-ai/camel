# Contributing to CAMEL

We greatly appreciate your enthusiasm in supporting the CAMEL project! As an open-source initiative in a swiftly advancing domain, we wholeheartedly welcome contributions in various forms. These can include introducing new features, enhancing infrastructure, improving documentation, or fixing bugs.

## Guidelines

### Contributing to the Code

If you're eager to contribute to this project, that's fantastic! We're thrilled to have your support. Just remember to use the provided [pull request template](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) when opening your pull requests. Make sure to mention any related issues and tag the relevant maintainers, too.

Keep in mind that pull requests must pass the formatting, linting, and testing checks before they can be merged. You can find instructions on running these checks locally under the [Common Tasks](#-common-tasks) section.

Ensuring excellent documentation and thorough testing is absolutely crucial. If you:
- Fix a bug
  - Add a relevant unit test when possible. These live in `test`.
- Make an improvement
  - Update any affected example console scripts in `examples`, Gradio demos in `apps` and documentation in `docs`.
  - Update unit tests when relevant.
- Add a feature
  - Add a demo script in `examples`.
  - Add unit tests.

We're a small team focused on building great things. If you have something in mind that you'd like to add or modify, opening a pull request is the ideal way to catch our attention.

### Issues

Our [issues](https://github.com/camel-ai/camel/issues) page on GitHub is regularly updated with bugs, improvements, and feature requests. We have a handy set of labels to help you sort through and find issues that interest you. Feel free to use these labels to keep things organized.

When you start working on an issue, please assign it to yourself so that others know it's being taken care of.

When creating a new issue, it's best to keep it focused on a specific bug, improvement, or feature. If two issues are related or blocking each other, it's better to link them instead of merging them into one.

We do our best to keep these issues up to date, but considering the fast-paced nature of this field, some may become outdated. If you come across any such issues, please give us a heads-up so we can address them promptly.

### 🙋Getting Help

Our aim is to make the developer setup as straightforward as possible. If you encounter any challenges during the setup process, don't hesitate to reach out to a maintainer. We're here to assist you and ensure that the experience is smooth not just for you but also for future contributors.

In line with this, we do have specific guidelines for code linting, formatting, and documentation in the codebase. If you find these requirements difficult or even just bothersome to work with, please feel free to get in touch with a maintainer. We don't want these guidelines to hinder the integration of good code into the codebase, so we're more than happy to provide support and find a solution that works for you.

## 🚀 Quick Start

To install requirements:

```bash
conda create -n camel python=3.9
conda activate camel
pip install -r requirements.txt
```

Once you run these commands, all the necessary dependencies for running the package, examples, linting, formatting, tests, and coverage will be installed.

Now, you should be all set to execute the common tasks outlined in the next section. To verify, go ahead and run `pytest .` – this should ensure that all tests pass successfully.

## Common Actions

### Linting & formatting

```bash
flake8
isort .
```

### Coverage

Code coverage, which measures the extent to which unit tests cover the code, is useful for identifying both more and less robust areas of the codebase.

To generate a report showing the current code coverage, execute the following:

```bash
pytest --cov --cov-report=html
```

The report can be found at `htmlcov/index.html`.

#### Tests

Unit tests cover modular logic that does not require calls to outside APIs. Currently the test setup requires OpenAI API key to test the framework, thus resembling integration tests.

To run tests:

```bash
pytest .
```

The tests expect `.env` file with your OpenAI API key in the repo root if developing with VSCode:
```
OPENAI_API_KEY=sk-XXXXXXXX
```

## Documentation

### Contribute to Documentation

The documentation is primarily generated automatically by [Sphinx](https://www.sphinx-doc.org/en/master/) using the code.

As a result, we kindly request that you provide comprehensive documentation for all classes and methods to ensure high-quality documentation coverage.

### Build Documentation Locally

You can build the documentation as outlined below:

```bash
sphinx-build docs docs/_build
```

## Release Process

As of now, CAMEL is in active development thus not published to PyPI yet.

CAMEL follows the [semver](https://semver.org/) versioning standard. As pre-1.0 software, even patch releases may contain [non-backwards-compatible changes](https://semver.org/#spec-item-4). Currently the major version is 0 and the minor version are being incremented and releases are made once the maintainers feel that a significant body of changes is accumulated.

### Recognition

If your contribution has been included in a release, we'd love to give you credit on Twitter, but only if you're comfortable with it!

If you have a Twitter account that you would like us to mention, please let us know either in the pull request or through another communication method. We want to make sure you receive proper recognition for your valuable contributions.

