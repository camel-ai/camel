---
name: skill-creator
description: Guide for creating effective skills. Use when you need to create or update a skill that adds specialized knowledge, workflows, or tool integrations.
license: Complete terms in LICENSE.txt
---

# Skill Creator

This skill provides guidance for creating effective skills.

## About Skills

Skills are modular, self-contained packages that extend your capabilities by providing
specialized knowledge, workflows, and tools. Think of them as onboarding guides for specific
domains or tasks.

### What Skills Provide

1. Specialized workflows - Multi-step procedures for specific domains
2. Tool integrations - Instructions for working with specific file formats or APIs
3. Domain expertise - Company-specific knowledge, schemas, business logic
4. Bundled resources - Scripts, references, and assets for complex and repetitive tasks

## Core Principles

### Concise is Key

The context window is shared across system prompts, conversation history, and other skills.
Only add context that is truly needed. Challenge each piece of information:
"Is this needed to complete the task reliably?" Prefer concise examples over long prose.

### Set Appropriate Degrees of Freedom

Match the level of specificity to the task's fragility and variability:

- High freedom (text-based instructions): Multiple approaches are valid.
- Medium freedom (pseudocode or scripts with parameters): A preferred pattern exists.
- Low freedom (specific scripts, few parameters): Consistency is critical.

Think of exploration: a narrow bridge needs guardrails, an open field allows many routes.

### Anatomy of a Skill

Every skill consists of a required SKILL.md file and optional bundled resources:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter metadata (required)
│   │   ├── name: (required)
│   │   └── description: (required)
│   └── Markdown instructions (required)
└── Bundled Resources (optional)
    ├── scripts/          - Executable code (Python/Bash/etc.)
    ├── references/       - Documentation intended to be loaded as needed
    └── assets/           - Files used in output (templates, icons, fonts)
```

#### SKILL.md (required)

Every SKILL.md consists of:

- Frontmatter (YAML): `name` and `description`. These are the only fields used to
  determine when the skill should be used. Be explicit about triggers and contexts.
- Body (Markdown): Instructions and guidance for using the skill. Read only when needed.

#### Bundled Resources (optional)

##### Scripts (`scripts/`)

Executable code for tasks that require deterministic reliability or are repeatedly rewritten.

- When to include: Repeated code or fragile operations
- Example: `scripts/rotate_pdf.py` for PDF rotation tasks
- Benefits: Token efficient, deterministic, can be executed without reading into context
- Note: You may still need to read scripts for patching or environment-specific changes

##### References (`references/`)

Documentation intended to be loaded into context as needed.

- When to include: Detailed docs, schemas, policies, API specs
- Examples: `references/schema.md`, `references/policies.md`, `references/api.md`
- Best practice: Keep SKILL.md lean and point to references for details
- Avoid duplication: Details live in references, not in SKILL.md

##### Assets (`assets/`)

Files not intended for context, but used in outputs.

- When to include: Templates, images, icons, boilerplate code, fonts
- Examples: `assets/logo.png`, `assets/slides.pptx`, `assets/frontend-template/`

#### What to Not Include in a Skill

Do not create extra docs like README.md, INSTALLATION_GUIDE.md, QUICK_REFERENCE.md,
CHANGELOG.md. Keep only files needed for the skill to do its job.

### Progressive Disclosure Design Principle

Skills use a three-level loading system to manage context efficiently:

1. Metadata (name + description) - Always in context
2. SKILL.md body - Read when the skill is relevant
3. Bundled resources - Read or run only as needed

Keep SKILL.md under ~500 lines. Split detailed or variant-specific content into references.

#### Progressive Disclosure Patterns

**Pattern 1: High-level guide with references**

```markdown
# PDF Processing

## Quick start

Extract text with pdfplumber:
[code example]

## Advanced features

- Form filling: See references/FORM_FILLING.md
- API reference: See references/REFERENCE.md
- Examples: See references/EXAMPLES.md
```

**Pattern 2: Domain-specific organization**

```
bigquery-skill/
├── SKILL.md (overview and navigation)
└── references/
    ├── finance.md
    ├── sales.md
    ├── product.md
    └── marketing.md
```

**Pattern 3: Conditional details**

```markdown
# DOCX Processing

## Creating documents

Use docx-js for new documents. See references/DOCX-JS.md.

## Editing documents

For simple edits, modify the XML directly.

For tracked changes: See references/REDLINING.md
For OOXML details: See references/OOXML.md
```

**Guidelines:**

- Avoid deeply nested references; keep references one level deep from SKILL.md.
- For reference files longer than 100 lines, add a table of contents.

## Skill Creation Process

1. Understand the skill with concrete examples
2. Plan reusable skill contents (scripts, references, assets)
3. Initialize the skill (create folder + SKILL.md)
4. Edit the skill (implement resources and write SKILL.md)
5. Iterate based on real usage

### Step 1: Understanding the Skill with Concrete Examples

Ask for concrete examples and likely triggers. Start with a few questions and
follow up as needed.

### Step 2: Planning the Reusable Skill Contents

For each example, identify what should be captured in scripts, references, or assets.

### Step 3: Initializing the Skill

Create the skill folder with a SKILL.md template and only the resource folders you need.

### Step 4: Edit the Skill

Write in imperative form. Keep the body focused on workflows and decisions. Point to
references for detailed content.

### Step 5: Iterate

After real usage, refine the skill based on observed failures or friction.
