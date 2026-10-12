"""LangGraph workflow:  planner -> architect -> coder (loops once per file) -> END"""
import json
from typing import Iterator, TypedDict

from langgraph.graph import END, StateGraph

from .llm import get_llm, invoke_json, invoke_text
from .prompts import ARCHITECT_PROMPT, CODER_PROMPT, PLANNER_PROMPT
from .states import Plan, TaskPlan
from .tools import list_files, new_project_dir, read_file, write_file

MAX_CONTEXT_CHARS = 14000


class AgentState(TypedDict, total=False):
    user_prompt: str
    model: str
    project_dir: str
    plan: dict
    tasks: list[dict]
    current_step: int
    status: str


def planner_agent(state: AgentState) -> dict:
    llm = get_llm(state.get("model"))
    plan = invoke_json(llm, PLANNER_PROMPT, state["user_prompt"], Plan)
    project_dir = new_project_dir(plan.name)
    return {
        "plan": plan.model_dump(),
        "project_dir": str(project_dir),
        "status": f"Planner: '{plan.name}' needs {len(plan.files)} files",
    }


def architect_agent(state: AgentState) -> dict:
    llm = get_llm(state.get("model"))
    user = f"User request:\n{state['user_prompt']}\n\nProject plan:\n{json.dumps(state['plan'], indent=2)}"
    task_plan = invoke_json(llm, ARCHITECT_PROMPT, user, TaskPlan)
    return {
        "tasks": [t.model_dump() for t in task_plan.implementation_steps],
        "current_step": 0,
        "status": f"Architect: created {len(task_plan.implementation_steps)} engineering tasks",
    }


def _existing_context(project_dir: str, skip: str) -> str:
    parts, used = [], 0
    for rel in list_files(project_dir):
        if rel == skip:
            continue
        body = read_file(project_dir, rel)
        chunk = f"--- {rel} ---\n{body}\n"
        if used + len(chunk) > MAX_CONTEXT_CHARS:
            parts.append(f"--- {rel} --- (omitted, too long)\n")
            continue
        parts.append(chunk)
        used += len(chunk)
    return "".join(parts) or "(no files written yet)"


def coder_agent(state: AgentState) -> dict:
    llm = get_llm(state.get("model"), temperature=0.1)
    step = state["current_step"]
    task = state["tasks"][step]
    total = len(state["tasks"])

    all_tasks = "\n".join(f"- {t['filepath']}: {t['task_description']}" for t in state["tasks"])
    user = (
        f"Project plan:\n{json.dumps(state['plan'], indent=2)}\n\n"
        f"All engineering tasks:\n{all_tasks}\n\n"
        f"Files already written:\n{_existing_context(state['project_dir'], task['filepath'])}\n\n"
        f"YOUR TASK -> write the complete file `{task['filepath']}`:\n{task['task_description']}\n\n"
        "Output only the file contents."
    )
    code = invoke_text(llm, CODER_PROMPT, user)
    write_file(state["project_dir"], task["filepath"], code)
    return {
        "current_step": step + 1,
        "status": f"Coder: wrote {task['filepath']} ({step + 1}/{total})",
    }


def _route(state: AgentState) -> str:
    return "coder" if state.get("current_step", 0) < len(state.get("tasks", [])) else END


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("planner", planner_agent)
    g.add_node("architect", architect_agent)
    g.add_node("coder", coder_agent)
    g.set_entry_point("planner")
    g.add_edge("planner", "architect")
    g.add_conditional_edges("architect", _route, {"coder": "coder", END: END})
    g.add_conditional_edges("coder", _route, {"coder": "coder", END: END})
    return g.compile()


def run_stream(user_prompt: str, model: str | None = None) -> Iterator[tuple[str, dict]]:
    """Yield (node_name, state_update) as each agent finishes."""
    graph = build_graph()
    state = {"user_prompt": user_prompt}
    if model:
        state["model"] = model
    for event in graph.stream(state, config={"recursion_limit": 150}, stream_mode="updates"):
        for node, update in event.items():
            yield node, update
