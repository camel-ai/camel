---
name: skill-creator
description: Create or update focused, CAMEL-compatible agent skills with only the instructions and resources their workflows need. Use when designing, scaffolding, validating, testing, or packaging a reusable skill for SkillToolkit; do not use for ordinary code or documentation that does not need a skill.
---

# Skill Creator

Create skills that give CAMEL agents useful, non-obvious guidance without
constraining unrelated work.

## Core principles

- **Assume the agent is capable.** Include only context that changes its
  decisions or makes repeated work more reliable. Remove generic advice,
  duplicated explanations, and speculative edge cases.
- **Preserve user intent and authority.** A skill supports the requested task;
  it does not broaden the task, select a different product, or grant permission
  for external or destructive actions.
- **Match specificity to risk.** Use flexible instructions when several
  approaches are valid. Use exact sequences or deterministic scripts when an
  operation is fragile, safety-sensitive, or must be repeatable.
- **Keep discovery precise.** The `description` is visible before the body and
  is the primary trigger. State the job, likely trigger terms, and any boundary
  needed to prevent common false matches.
- **Disclose details progressively.** Keep the shared workflow in `SKILL.md`.
  Put conditional details in directly linked references and load only the
  resources needed for the current request.
- **Prefer the smallest useful bundle.** Start instruction-only. Add a script,
  reference, or asset only when it has a concrete, recurring purpose.

## CAMEL skill contract

A skill is a directory with one required file and optional resources:

```text
skill-name/
|-- SKILL.md          Required frontmatter and instructions
|-- scripts/          Optional deterministic helpers
|-- references/       Optional guidance loaded only when relevant
`-- assets/           Optional templates or files used in output
```

For repository-scoped CAMEL skills, prefer
`<repo-root>/.camel/skills/<skill-name>/`. `SkillToolkit` also discovers
repository skills under `.agents/skills`, user skills under `~/.camel/skills`
and `~/.config/camel/skills`, and system skills under `/etc/camel/skills`.

Design for these runtime behaviors:

- `SkillToolkit` initially exposes each skill's `name`, `description`, path,
  scope, and direct child entries. It loads the body only after the agent calls
  `load_skill`.
- Loaded content includes the skill's base directory. Use paths relative to
  that directory when referring to bundled resources.
- Repository skills take precedence over user and system skills with the same
  name. Keep names unique and make the directory name match the frontmatter
  `name`.
- Skill discovery is cached. Call `clear_cache()` or recreate the toolkit when
  testing changes in a running process.
- `SkillToolkit` loads instructions but does not execute scripts. Give the
  agent `TerminalToolkit` or another appropriate execution tool when a skill
  requires runnable helpers.
- Product-specific metadata is optional. Do not add files such as
  `agents/openai.yaml` unless a target host actually consumes them; CAMEL's
  `SkillToolkit` does not require them.

## Create or update a skill

Adapt the workflow to the request. Skip steps that add no value, but verify the
finished skill against realistic use.

### 1. Define the job and trigger boundary

Identify:

- the outcome the skill should help produce;
- two or three realistic requests that should trigger it;
- nearby requests that should not trigger it;
- non-obvious constraints, tools, data, or output requirements.

Ask the user only for missing information that would materially change the
skill. For an existing skill, inspect its current files and callers before
removing or renaming anything.

### 2. Plan the minimum bundle

Use `SKILL.md` alone when instructions are sufficient. Add resources only for
these reasons:

- `scripts/`: logic that would otherwise be rewritten, or operations needing
  deterministic behavior;
- `references/`: maintained schemas, policies, APIs, or substantial guidance
  needed only in some modes;
- `assets/`: templates, fonts, images, boilerplate, or other files copied or
  adapted into the result.

Do not add placeholder directories, README files, changelogs, installation
guides, or duplicated quick references without a concrete requirement.

### 3. Initialize or edit

For a new skill, either create the directory and `SKILL.md` directly or use the
bundled initializer when its scaffold is useful:

```bash
python <skill-creator-base>/scripts/init_skill.py \
  <skill-name> --path <repo-root>/.camel/skills
```

The current initializer creates example resource directories. Delete every
placeholder and directory the finished skill does not need. Do not initialize
an existing skill again.

Use lowercase letters, digits, and single hyphens for names, with a maximum of
64 characters.

### 4. Write for progressive disclosure

In frontmatter:

- Keep `name` equal to the skill directory name.
- Write a concise, discriminating `description` that says what the skill does
  and when it applies. Front-load the main use case because hosts may shorten
  long descriptions.
- Keep required metadata to `name` and `description`. Add supported optional
  fields only when the target environment needs them.

In the body:

- Use direct instructions and decision criteria, not background the agent
  already knows.
- State inputs, outputs, important invariants, and stopping conditions where
  they affect correctness.
- Link every supporting reference where it becomes relevant and explain when
  to read it. Avoid deep chains of references.
- Reuse scripts and assets explicitly rather than asking the agent to recreate
  them.
- Preserve real compatibility and authorization boundaries. Do not turn one
  observed failure into a universal rule without evidence.

For conditional patterns, read only the applicable bundled guide:

- For sequential or branching procedures, read
  [references/workflows.md](references/workflows.md).
- For strict output structures or examples, read
  [references/output-patterns.md](references/output-patterns.md).

### 5. Validate implementation

Run the bundled validator from any working directory:

```bash
python <skill-creator-base>/scripts/quick_validate.py <skill-directory>
```

Then verify the behavior that validation cannot prove:

- Run every new or changed helper script with representative inputs.
- Instantiate `SkillToolkit` with the intended repository root as
  `working_directory` and confirm the skill appears in `list_skills()`.
- Confirm `list_skill_files()` exposes the intended resources and
  `load_skill()` returns the body with the correct base directory.
- If scripts are required, test the agent with both `SkillToolkit` and the
  execution toolkit the workflow expects.

### 6. Evaluate and iterate

Test trigger quality and execution quality separately:

1. Try the realistic should-trigger and should-not-trigger requests from step
   1. Include paraphrases rather than matching only the description's wording.
2. Run a small set of representative tasks with the skill loaded. When useful,
   compare against the same tasks without the skill to check that it adds
   value.
3. Inspect the actual decisions and outputs, collect user feedback when output
   quality is subjective, and identify the smallest supported correction.
4. Re-run the affected cases and retain changes only when they improve the
   intended behavior without broadening false triggers.

Use the CAMEL model and agent configuration already chosen for the task. Do not
introduce a provider-specific CLI merely to evaluate a CAMEL skill. Independent
or parallel agent evaluation is optional when available and justified; it is
not a prerequisite for creating a useful skill.

### 7. Package only when needed

If the user needs a distributable `.skill` archive, run:

```bash
python <skill-creator-base>/scripts/package_skill.py \
  <skill-directory> [output-directory]
```

The packager validates first and excludes common local, credential, cache, and
build artifacts. Inspect the archive contents before delivery. Do not package
an intermediate skill when repository-local use is the requested outcome.

## Completion criteria

A skill is complete when:

- its trigger boundary is clear and tested with positive and negative cases;
- its instructions preserve task scope and contain only useful guidance;
- every bundled resource is necessary, discoverable, and verified;
- CAMEL can discover and load it from the intended root;
- no scaffold placeholders or local artifacts remain;
- packaging succeeds when distribution was requested.
