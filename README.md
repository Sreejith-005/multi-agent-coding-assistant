# 🤖 Coder Buddy: Multi-Agent Coding Assistant

Type a request like *"Build a calculator web app with add, subtract, multiply and divide buttons"*
and a small AI engineering team builds the project file by file.

```
 user prompt
     │
     ▼
┌──────────┐   Plan (name, stack, features, files)
│ Planner  │───────────────┐
└──────────┘               ▼
                    ┌────────────┐   ordered per-file tasks
                    │ Architect  │──────────────┐
                    └────────────┘              ▼
                                         ┌────────────┐  ◄─┐ loops once
                                         │   Coder    │────┘ per file
                                         └─────┬──────┘
                                               ▼
                                   generated_projects/<name>-<timestamp>/
```

| Agent | Job |
|-------|-----|
| **Planner** | Reads the request, outputs a structured `Plan` (stack, features, file list) |
| **Architect** | Turns the plan into one detailed `ImplementationTask` per file, dependencies first |
| **Coder** | Writes each file with the plan, all tasks and already-written files as context, then saves it to disk |

Built with **LangGraph**, **Groq** (Kimi K2 / Qwen 3) and **Streamlit**.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then paste your Groq key
```

Free Groq key: https://console.groq.com/keys

## Run

**Web UI**
```bash
streamlit run app.py
```
Pick a model, enter a prompt, click *Generate project*. You can browse the code, preview
`index.html` apps, and download the project as a `.zip`.

**CLI**
```bash
python main.py "Build a to-do list web app with local storage" --model qwen/qwen3-32b
```

## Project layout

```
app.py               Streamlit interface
main.py              CLI entry point
agent/
  states.py          Pydantic schemas (Plan, TaskPlan, ...)
  prompts.py         System prompts for the three agents
  llm.py             Groq client, JSON/text helpers with retries
  tools.py           Sandboxed file tools + zip export
  graph.py           LangGraph workflow
```

## Design notes

- **Sandboxed writes:** every path is resolved inside the project folder, so `../` or absolute
  paths from the model are rejected.
- **Model-agnostic JSON:** the Planner and Architect parse JSON themselves (with retry + error
  feedback) instead of relying on tool-calling, so Kimi K2, Qwen 3 or any other Groq model works.
  `<think>` blocks from Qwen 3 are stripped automatically.
- **Context-aware coding:** the Coder sees previously written files (capped at ~14k chars) so
  imports, HTML ids and routes line up.

## Troubleshooting

- *Rate limit (429)*: free-tier Groq has per-minute token limits. Wait a minute, try a smaller
  prompt, or switch model.
- *Model not found*: Groq rotates model ids. Check https://console.groq.com/docs/models and set
  `GROQ_MODEL` or use the custom model field in the sidebar.

## Ideas to extend

- Add a **Reviewer/Debugger agent** that runs the code (or lints it) and sends errors back to the Coder.
- Let the Coder use tools (`read_file`, `write_file`, `run_command`) in a ReAct loop.
- Support iterative edits: "now add a history panel" on an existing project.
- Port the graph to **CrewAI** (Planner/Architect/Coder as `Agent`s with sequential `Task`s).
- Build a React frontend that calls the graph through a FastAPI endpoint.
