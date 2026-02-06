# CLAUDE.md - AI Assistant Guide for Gestionale

## Project Overview

**Gestionale** ("Complete Management System") is an Italian business management application. The project is in its initial setup phase — no application code, dependencies, or configuration exist yet beyond this file and a minimal README.

## Repository State

- **Status**: Greenfield project (initial setup phase)
- **Repository**: `tlf-hub/Gestionale`
- **Primary language**: To be determined
- **Current contents**: README.md, CLAUDE.md

## What Needs to Be Built

This is a "gestionale completo" — a complete business management system. Typical features for this type of Italian business software include:

- Customer/supplier management (anagrafica clienti/fornitori)
- Invoice management (fatturazione elettronica)
- Inventory/warehouse management (gestione magazzino)
- Accounting (contabilità)
- Reporting and analytics
- User authentication and role-based access

## Development Guidelines

### For AI Assistants Working on This Project

1. **Ask before assuming** — Since the project has no code yet, always confirm technology choices (language, framework, database) with the user before scaffolding.
2. **Keep it simple** — Start with minimal viable structure. Don't over-engineer the initial setup.
3. **Italian context** — This is an Italian business tool. Expect Italian-language UI, Italian fiscal/tax requirements (e.g., fatturazione elettronica, codice fiscale, partita IVA), and Italian date/currency formats.
4. **Incremental development** — Build features one at a time. Don't scaffold the entire application in one pass.

### Git Workflow

- Default branch: `main`
- Feature branches: `claude/<feature-description>-<session-id>`
- Write clear, descriptive commit messages
- Push to feature branches, not directly to `main`

### Code Style (to be established)

Once the tech stack is chosen, this section should be updated with:
- Linting and formatting configuration
- Naming conventions
- File/folder organization standards
- Testing requirements

## File Structure

```
Gestionale/
├── CLAUDE.md          # This file — AI assistant guide
└── README.md          # Project description
```

> **Update this section** as directories and files are added to the project.

## Commands

No build, test, or run commands are configured yet. Update this section as tooling is added.

## Architecture Decisions

Document key decisions here as the project evolves:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Project type | TBD | — |
| Frontend framework | TBD | — |
| Backend framework | TBD | — |
| Database | TBD | — |
| Authentication | TBD | — |
| Deployment target | TBD | — |

## Notes for Future Sessions

- This CLAUDE.md should be updated after every significant change to the project structure, tooling, or conventions.
- When the tech stack is chosen, add specific linting commands, test commands, and build steps to the "Commands" section.
- Add environment variable documentation once `.env` files are introduced.
