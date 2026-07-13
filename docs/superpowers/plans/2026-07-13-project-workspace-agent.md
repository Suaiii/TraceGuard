# TraceGuard Project Workspace Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the inventory-only AGENTS.md with a project-level operating standard grounded in the live TraceGuard code, competition workspace, and GitHub workflow.

**Architecture:** Keep one root AGENTS.md as the normative project reference. It separates product contracts, repository code, local competition assets, experiment evidence, report rules, and GitHub delivery while declaring the AI竞赛 checkout as the primary workspace.

**Tech Stack:** Markdown, Git, GitHub, FastAPI, Pydantic, PyTorch, vanilla Web frontend, pytest.

---

### Task 1: Reframe the workspace contract

**Files:**
- Modify: `AGENTS.md`

- [x] Replace the inventory-only title and scope with the formal TraceGuard project identity.
- [x] Record source-of-truth priority and the relationship between the two local checkouts.
- [x] Preserve local competition originals as untracked assets.

### Task 2: Encode implementation and validation rules

**Files:**
- Modify: `AGENTS.md`

- [x] Document architecture, module boundaries, API contracts, and team responsibilities.
- [x] Document Issue, Routing Gate, implementation, test, browser QA, review, and GitHub workflows.
- [x] Document experiment, report, model, dataset, and inventory constraints.

### Task 3: Verify and publish

**Files:**
- Modify: `AGENTS.md`
- Create: `docs/superpowers/plans/2026-07-13-project-workspace-agent.md`

- [x] Check the document for stale FakeTrace-first framing, missing project modules, placeholders, and contradictory Git paths.
- [x] Run `git diff --check` and inspect the exact staged files.
- [ ] Create an Issue and PR, push the branch, and merge after verification.
