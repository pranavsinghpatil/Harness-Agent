# AI Agents Operating Guide (`agents.md`)

Welcome to the **Agent Harness** operational guide for the **Trueforge Hackathon** project. This document serves as the single source of truth for AI coding agents (including Qodo, Cursor, Claude Code, Antigravity, and GitHub Copilot) and human teammates collaborating in this repository.

---

## 🎯 Purpose & Principles

This repository follows the **Agent Harness Architecture** designed to maximize speed, code quality, and seamless handoffs across a 4-person engineering team working with AI coding agents.

### Core Tenets
1. **Modularity First:** Small, composable, single-purpose functions and components. Avoid monolithic files.
2. **Strict Type Safety:** Always declare explicit type definitions (TypeScript interfaces/types or Python type hints with Pydantic). Never use untyped `any` or ambiguous dictionaries without schema validation.
3. **Security by Design:** Never commit API keys, tokens, or credentials. Always reference environment variables defined in `.env.example`.
4. **Context-Rich Explanations:** Include inline comments that explain *why* non-obvious architecture or business logic decisions were made to streamline handoffs and context-switching.
5. **Automated Verification:** Every new feature, endpoint, or utility must be accompanied by appropriate test coverage and validation.

---

## 📁 Repository Layout & Context Map

Agents must understand the structure of the workspace before reading or modifying files:

| Directory | Purpose | Agent Focus & Rules |
| :--- | :--- | :--- |
| `backend/` | API services, controllers, business logic | Keep endpoints RESTful/gRPC/GraphQL compliant, validate inputs via schemas, handle errors gracefully. |
| `frontend/` | UI client, web app, views | Component-driven UI, state management, accessibility (a11y), responsive design. |
| `schemas/` | Database schemas, request/response models | Single source of truth for data contracts across frontend and backend. |
| `configs/` | Shared configs, environment schemas | Cross-service configuration definitions, constants, and runtime flags. |
| `data/` | Datasets, seed scripts, mock data | Test fixtures, sample inputs, mock responses for offline development. |
| `docs/` | Architecture specs, API documentation | ADRs (Architecture Decision Records), flowcharts, endpoint documentation. |
| `experiments/` | PoCs, model benchmarking, exploratory R&D | Isolated prototypes; clean up or migrate to `backend`/`frontend` once proven. |
| `scripts/` | Tooling, migration runners, automation | CI/CD helpers, database seeders, dev setup automations. |
| `.ai/` | AI prompts, system context, harness docs | Agent guidelines (`agents.md`), specialized prompt templates, tool definitions. |
| `.cursor/` | IDE rules and settings | Editor-level agent constraints and rules (`.cursorrules`). |

---

## 🤖 Agent Roles & Workflows

When operating within this codebase, agents should adopt the appropriate persona based on the task:

### 1. 🏗️ Architect Agent
- **Responsibilities:** Define schema models in `schemas/`, design API interfaces, establish folder structure, and produce architecture specs in `docs/`.
- **Guidelines:** Ensure clear boundaries between layers and keep interfaces decoupled.

### 2. ⚡ Feature Developer Agent
- **Responsibilities:** Implement features across `backend/` and `frontend/` based on contracts defined in `schemas/`.
- **Guidelines:** Follow existing coding styles, use async patterns properly, and maintain separation between presentation, state, and business logic.

### 3. 🧪 Quality & Test Engineer (Qodo / Test Agent)
- **Responsibilities:** Generate comprehensive unit, integration, and end-to-end tests; analyze edge cases; verify boundary conditions; validate error handling.
- **Guidelines:** 
  - Aim for meaningful assertion-based test coverage.
  - Test happy paths, invalid inputs, network failures, and unauthorized requests.
  - Keep test fixtures organized in `data/` or adjacent `__tests__`/`tests/` directories.

### 4. 🛡️ Reviewer & Security Agent
- **Responsibilities:** Static analysis, lint checks, dependency vulnerability scanning, PR review summaries.
- **Guidelines:** Enforce rules from `.cursorrules`, catch security anti-patterns (e.g. SQL injection, unescaped HTML, exposed secrets), and verify performance implications.

---

## 📋 Coding Conventions & Guidelines

### TypeScript / JavaScript (Frontend & Node.js Backend)
- Use ES Modules (`import`/`export`).
- Strict typing with interfaces and type aliases; avoid `any`.
- Handle promises using `async`/`await` with structured `try/catch` error handling.
- Functional component patterns with hooks for React frontend code.

### Python (Backend / AI Services)
- PEP 8 compliant, type-annotated (`typing` / Python 3.10+ union types `X | Y`).
- Pydantic models for request/response serialization and validation.
- Clear docstrings (Google or NumPy format) for modules, classes, and public functions.

### Error Handling & Logging
- Use structured error responses with HTTP status codes and actionable error messages:
  ```json
  {
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "The requested entity does not exist.",
      "details": {}
    }
  }
  ```
- Avoid raw `console.log` or unformatted `print` in production code; use a dedicated logger.

---

## 🔄 Git & Pull Request (PR) Standard

Agents contributing code must adhere to team git hygiene:

1. **Branch Naming:**
   - Feature branches: `feature/<feature-name>` or `t/<ticket-or-tool-name>` (e.g., `t/qodo`)
   - Fix branches: `fix/<issue-name>`
   - Documentation / AI Configs: `docs/<topic>` or `ai/<topic>`
2. **Commit Message Format:**
   - Use conventional commit messages: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
   - Example: `docs(ai): add comprehensive agents.md guide for AI harness`
3. **Pull Request Checklist:**
   - [ ] Clear title with conventional prefix.
   - [ ] Summary of changes explaining *what* was done and *why*.
   - [ ] Testing steps or automated tests included.
   - [ ] No sensitive credentials or secrets committed.
   - [ ] Tagged team members for review.

---

## 🛠️ Environment & Secrets Configuration

- All configurable values must be documented in [`.env.example`](file:///D:/GitRepo/harness/.env.example).
- Agents must never generate code that hardcodes API keys, tokens, database passwords, or private URLs.
- When adding new environment variables, always update `.env.example` with clear comments explaining the variable's purpose.
