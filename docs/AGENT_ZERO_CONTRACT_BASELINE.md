# Agent Zero Contract Baseline

**Status:** Independently verified from public Agent Zero documentation and public framework/plugin-index sources on 2026-08-03.

This document records only the contract required to begin an isolated plugin implementation. It is not a substitute for source-level and runtime verification before implementing framework-facing behavior.

## Verified plugin packaging facts

- User-owned plugins are installed under `/a0/usr/plugins/<plugin_name>/`; framework-root plugin directories must not be modified for a user plugin.
- A minimal plugin has `plugin.yaml` at repository/plugin root, a README, and may include `extensions/webui/` and `webui/`.
- Agent Zero plugins may provide Web UI surfaces, tools, settings, scripts, hooks, model providers, and integrations.
- Web UI extension changes require a browser refresh so Agent Zero rebuilds its extension list.
- The public plugin manifest examples establish `name`, `title`, `description`, and `version` as core fields. Built-in examples also use `settings_sections`, `per_project_config`, and `per_agent_config`.

## Verified publication constraints

If submitted to the public Plugin Index, the index folder name and this repository's `plugin.yaml.name` must match exactly and use lowercase letters, digits, and underscores. The intended public identity is therefore `neuro_core_2`.

An Index submission requires a repository-root `plugin.yaml`; the Index metadata separately identifies the GitHub repository. Publication is explicitly out of scope until functionality, evidence, packaging, and review gates are complete.

## Architectural consequences

1. Neuro Core 2 will install as an independent user plugin, never as a modification of framework-owned files.
2. The plugin begins with a root manifest and project/agent-scoped policy declaration.
3. The first runtime slice should be small, observable, and removable: one visible Workbench surface and no hidden lifecycle mutation.
4. Tools, APIs, lifecycle extensions, and storage adapters remain deferred until the precise source/runtime contract for each is checked.
5. A plugin adapter must translate framework inputs and outputs at the edge; the core memory domain cannot depend on framework-owned classes.

## Still unverified

- Exact current Web UI component/registration contract.
- Current API handler and authentication contract.
- Tool response and prompt-discovery contract.
- The lifecycle extension point appropriate for automatic capture or retrieval injection.
- Runtime behavior of project and agent configuration precedence.
- Supported test command and container-level smoke procedure.

Each item needs a targeted source or runtime check before implementation.
