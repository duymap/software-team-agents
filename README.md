# Software Team Agents

A multi-agent system that simulates a software development team to plan and generate complete project codebases. Five specialized AI agents — PM, Architect, Developer, Reviewer, and QA — collaborate through a structured workflow powered by local LLMs.

Built on [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) with support for [Ollama](https://ollama.com/) and [LM Studio](https://lmstudio.ai/) as LLM backends.

## How It Works

The system runs in two phases:

### Phase 1: Planning

Your project idea flows through a deterministic agent pipeline:

```
User Input → PM → Architect → Developer → Reviewer → QA → Plan Output
                                  ^            |
                                  |  (revision) |
                                  +-------------+
```

| Agent | Role | Model Type |
|-------|------|------------|
| **PM** | Analyzes the idea, extracts requirements, defines scope, creates task breakdown | Reasoning |
| **Architect** | Proposes tech stack, designs system architecture, data models, and data flow | Reasoning |
| **Developer** | Creates file structure, implementation plan, code snippets, and API design | Code |
| **Reviewer** | Reviews for consistency, feasibility, gaps, and best practices | Code |
| **QA** | Defines test strategy, key test cases, acceptance criteria, and gives final sign-off | Reasoning |

The **Reviewer** can send work back to the **Developer** for revision (up to 2 rounds) before the plan is approved and passed to QA.

### Phase 2: Code Generation

After planning, you can optionally generate the full project codebase. A dedicated **Code Generator** agent reads the entire plan and produces production-ready source files — configs, models, services, API routes, Dockerfiles, and more — written to a directory of your choice.

The generator supports multi-turn continuation: if the codebase is too large for a single response, it automatically continues generating across up to 5 rounds.

## Prerequisites

- **Python 3.10+**
- **Ollama** or **LM Studio** running locally with a model loaded
  - Recommended: `qwen3.5-35b-a3b` or any instruction-following model
  - The same model can be used for both reasoning and code roles, or you can configure separate models

## Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/duymap/software-team-agents.git
   cd software-team-agents
   ```

2. **Create a virtual environment and install dependencies:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` to match your setup:

   ```env
   # LLM Provider: "ollama" or "lmstudio"
   LLM_PROVIDER=lmstudio

   # Base URL for the LLM provider
   # LM Studio default: http://localhost:1234
   # Ollama default: http://localhost:11434
   LLM_BASE_URL=http://localhost:1234

   # Context window size (ollama only)
   LLM_NUM_CTX=8192

   # Reasoning model (used by PM, Architect, QA)
   REASONING_MODEL=qwen3.5-35b-a3b
   REASONING_TEMPERATURE=0.7

   # Code model (used by Developer, Reviewer, Code Generator)
   CODE_MODEL=qwen3.5-35b-a3b
   CODE_TEMPERATURE=0.3
   ```

4. **Start your LLM backend:**

   For LM Studio: Load your model and start the server (default port 1234).

   For Ollama:
   ```bash
   ollama serve
   ollama pull qwen3.5-35b-a3b  # or your preferred model
   ```

## Usage

```bash
python main.py
```

The interactive CLI will:

1. **Prompt for your project idea** — describe what you want to build, or press Enter to use the built-in demo (a REST API for a task management app).
2. **Run the planning pipeline** — watch each agent contribute in real time with color-coded, streaming output.
3. **Ask about code generation** — respond with:
   - `yes` then enter a folder path
   - `yes ~/projects/my-app` to specify the path inline
   - `no` to skip code generation

### Example

```
> Describe your project idea (or press Enter for demo)
> Build a real-time chat application with WebSocket support, user authentication, and message history

[PM] pm
## Requirements
- User registration and login with JWT authentication
- Real-time messaging via WebSockets
...

[ARCH] architect
## Tech Stack
- Node.js + Express for REST API
- Socket.io for WebSocket layer
...

[DEV] developer
## File Structure
├── src/
│   ├── config/
│   ├── models/
│   ├── routes/
...

[REV] reviewer
## Review Summary
The implementation plan is well-structured...
## Verdict
APPROVED

[QA] qa
## Test Strategy
...
FINAL SIGN-OFF: Project plan is complete.

> Generate the codebase? (yes/no, or "yes ~/path/to/folder")
> yes ~/projects/chat-app

Generating files...
  Created: package.json
  Created: src/index.js
  Created: src/config/database.js
  ...
  ✓ 15 files created in 45.2s
```

## Project Structure

```
software-team-agents/
├── main.py           # CLI entry point, interactive prompts, streaming output
├── agents.py         # Agent definitions and system prompts for all 5 roles
├── orchestrator.py   # Workflow graph: agent pipeline, review gate, routing logic
├── codegen.py        # Code generation phase: plan summarization and file extraction
├── config.py         # LLM provider configuration (Ollama / LM Studio)
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
└── .gitignore
```

## Architecture Details

### Workflow Engine

The orchestrator uses `WorkflowBuilder` from Microsoft Agent Framework to define a directed graph of agent executors:

- **Linear edges** connect PM → Architect → Developer → Reviewer
- A **ReviewGate** executor inspects the reviewer's verdict and routes conditionally:
  - `APPROVED` → QA agent
  - `REVISION NEEDED` → back to Developer (up to 2 revisions, then auto-approves)
- A **Finish** executor captures QA's output and yields the full conversation

### LLM Configuration

Two client types are supported:

| Provider | Client | Notes |
|----------|--------|-------|
| **LM Studio** | `OpenAIChatClient` | Connects via OpenAI-compatible API at `/v1/` |
| **Ollama** | `OllamaChatClient` | Native Ollama client with `num_ctx` support |

Agents are split into two groups by model type:
- **Reasoning** (PM, Architect, QA): Higher temperature (0.7) for creative planning
- **Code** (Developer, Reviewer, Code Generator): Lower temperature (0.3) for precise output

### Code Generation

The code generator uses a structured format (`###FILE: path### ... ###ENDFILE###`) to emit files that are parsed and written to disk. Path traversal attacks are prevented by rejecting paths containing `..`.

## License

MIT
