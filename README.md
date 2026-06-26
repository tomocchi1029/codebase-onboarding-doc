# Codebase Onboarding Doc

> Automatically generate **"Why" documentation** for your codebase — not what it does, but *why* it does it that way.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Why?

Existing code documentation tools (CodeSee, Swimm, Mintlify) tell you **what** the code does. But when you join a new team, the real questions are:

- **"Why is there a 500ms sleep before this API call?"**
- **"Why does this function have a TODO from 2019 that nobody fixed?"**
- **"Why is this module structured this way instead of the obvious approach?"**
- **"Why was this security check removed in commit abc123?"**

**Codebase Onboarding Doc** analyzes Git history, PR discussions, code comments, and the code itself to answer these "why" questions — automatically generating an onboarding document that explains the **reasoning and history** behind your codebase.

## Quick Start

```bash
pip install codebase-onboarding-doc

# Generate onboarding docs for a repo
codoc generate --repo ./my-project --output docs/onboarding.md

# Focus on specific directories
codoc generate --repo ./my-project --focus src/auth,src/api --output docs/auth-onboarding.md

# Include PR/commit history analysis
codoc generate --repo ./my-project --depth 500 --output docs/onboarding.md

# Generate interactive HTML
codoc generate --repo ./my-project --format html --output docs/onboarding.html
```

## Example Output

```markdown
# Onboarding Guide: my-project

## Architecture Overview

This is a Django REST API with a React frontend. The codebase follows
a modular architecture where each app is self-contained with its own
models, views, and serializers.

### Key Design Decisions

#### 1. Why does `auth/login.py` use a custom token implementation instead of Django's built-in auth?

**History**: Commit abc1234 (2023-06-15) by @alice
> "We switched to custom tokens because Django's session auth doesn't
> work well with our mobile app. The custom implementation supports
> token refresh and device-specific sessions."

**Impact**: This affects `auth/middleware.py`, `auth/tokens.py`, and
`api/views.py`. If you need to modify authentication, start with
`auth/tokens.py` — the token lifecycle is the core of the system.

#### 2. Why is there a 500ms sleep in `api/rate_limiter.py`?

**History**: Commit def5678 (2023-08-20) by @bob
> "This is a temporary workaround for a race condition in our Redis
> cluster. The proper fix is to use Redis transactions, but that
> requires upgrading our Redis version. See issue #234."

**Impact**: This is technical debt. The sleep directly affects API
latency. If you're working on performance, this is a known bottleneck.

#### 3. Why does `models/user.py` have a `legacy_id` field?

**History**: Commit ghi9012 (2022-01-10) by @charlie
> "We migrated from a legacy system and needed to maintain backward
> compatibility with the old API. The `legacy_id` maps to the old
> system's user IDs. We planned to remove it after 6 months, but
> external integrations still depend on it."

**Impact**: The `legacy_id` field is used in `api/legacy_views.py`
and is referenced by 3 external clients. Do NOT remove it without
coordinating with the integrations team.
```

## How It Works

```
┌─────────────┐   ┌──────────────┐   ┌──────────────┐   ┌───────────┐
│  Git History │──▶│  Code         │──▶│  LLM "Why"   │──▶│ Onboarding│
│  (commits,   │   │  Analysis    │   │  Analyzer    │   │  Doc      │
│   PRs,       │   │  (structure, │   │  (GLM/GPT/   │   │  (MD/HTML)│
│   issues)    │   │   patterns,  │   │   Claude)    │   │           │
│              │   │   anomalies) │   │              │   │           │
└─────────────┘   └──────────────┘   └──────────────┘   └───────────┘
                         │                  │
                    ┌────┴────┐      ┌──────┴──────┐
                    │ AST     │      │ 1. Why does │
                    │ analysis│      │    this exist│
                    │ Import  │      │ 2. Why this │
                    │ graph   │      │    approach? │
                    │ TODOs   │      │ 3. What's the│
                    │ Hacks   │      │    history?  │
                    └─────────┘      │ 4. What to   │
                                     │    watch for │
                                     └─────────────┘
```

1. **Git Archaeology**: Mine commit messages, PR descriptions, and blame data
2. **Code Analysis**: Detect patterns, anomalies, TODOs, hacks, and architectural decisions
3. **LLM Reasoning**: For each finding, answer "Why does this exist?" using history + code context
4. **Document Generation**: Produce a structured onboarding guide

## What It Detects

| Pattern | Example | How |
|---------|---------|-----|
| **Architectural decisions** | "Why microservices instead of monolith?" | Commit history + code structure |
| **Workarounds & hacks** | "Why is there a sleep(500)?" | Code anomalies + commit messages |
| **Technical debt** | "Why is this TODO still here?" | TODO/FIXME comments + age analysis |
| **Legacy code** | "Why does this old module exist?" | Git blame + import analysis |
| **Security decisions** | "Why was this check removed?" | Commit diffs + PR discussions |
| **Performance choices** | "Why use caching here?" | Code patterns + commit rationale |
| **Naming mysteries** | "Why is this function called 'foo'?" | Git history + code context |

## Configuration

```yaml
# .codoc.yml
llm:
  provider: openai
  model: glm-4.6
  api_key: ${LLM_API_KEY}

analysis:
  git_depth: 500              # number of commits to analyze
  focus_dirs: ["src/"]        # directories to focus on
  ignore_dirs: ["vendor/", "node_modules/"]
  detect_todos: true
  detect_hacks: true
  detect_legacy: true
  detect_security_changes: true

output:
  format: markdown             # markdown, html, json
  include_code_snippets: true
  include_commit_links: true
  max_sections: 20
```

## Installation (Development)

```bash
git clone https://github.com/tomocchi1029/codebase-onboarding-doc.git
cd codebase-onboarding-doc
pip install -e ".[dev]"
pytest
```

## License

MIT
