from __future__ import annotations

import os
import uuid
import sys
from pathlib import Path

# Add project root to path so src/ and personas/ are reachable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional

import yaml
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langsmith import traceable

# --- Project internals ---
from src.personality.schema import Persona

# ── Environment ────────────────────────────────────────────────────────────────
load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = "true"
if not os.environ.get("LANGCHAIN_PROJECT"):
    os.environ["LANGCHAIN_PROJECT"] = f"test-agent-monitoring-{uuid.uuid4().hex[:8]}"

print(f"Logging to LangSmith Project: {os.environ.get('LANGCHAIN_PROJECT')}")


# ── 1. Load & validate Persona ─────────────────────────────────────────────────
#
# Why validate against Pydantic schema at load-time?
# Fail-fast: surface malformed YAML *before* any LLM call is made, not mid-run.
_PERSONA_PATH = Path(__file__).parent.parent / "personas" / "counter.yaml"

with _PERSONA_PATH.open(encoding="utf-8") as fh:
    _raw = yaml.safe_load(fh)

persona: Persona = Persona.model_validate(_raw)

print(f"Loaded persona: '{persona.metadata.id}' v{persona.metadata.version}")
print(f"  target_model : {persona.metadata.target_model}")
print(f"  temperature  : {persona.config.temperature}")
print(f"  max_tokens   : {persona.config.max_tokens}")
print(f"  stop         : {persona.config.stop}")


# ── 2. Define Mock Tools ────────────────────────────────────────────────────────

@tool
def get_weather(location: str) -> str:
    """Returns the mock weather for a given location."""
    print(f"\n[Tool Execution] get_weather called for: {location}")
    if "taipei" in location.lower():
        return "It's rainy and 22°C."
    elif "tokyo" in location.lower():
        return "It's sunny and 18°C."
    return f"Weather data not found for {location}, but it's probably nice."


@tool
def calculate_sum(a: float, b: float) -> str:
    """Calculates the sum of two numbers."""
    print(f"\n[Tool Execution] calculate_sum called with: {a}, {b}")
    return f"The sum of {a} and {b} is {a + b}."


@tool
def fetch_user_settings(user_id: str) -> str:
    """Fetches user settings. Throws an error if user_id is '999'."""
    print(f"\n[Tool Execution] fetch_user_settings called for: {user_id}")
    if user_id == "999":
        raise ValueError("User not found or database connection failed.")
    return f"Settings for {user_id}: theme=dark, notifications=enabled."


tools = [get_weather, calculate_sum, fetch_user_settings]


# ── 3. Initialise LLM (wired to persona config) ────────────────────────────────
#
# Why pull config from the persona YAML rather than hard-coding?
#   • Single source of truth: behaviour changes live in the YAML, not scattered code.
#   • `stop` sequences let us honour the persona's output format constraints
#     (e.g. counter.yaml stops on </final_response>).
base_url = os.getenv("BASE_URL")
api_key  = os.getenv("API_KEY", "dummy")

# metadata.target_model is treated as the authoritative model name for this persona.
# Fall back to the env-var MODEL only when the persona leaves it at the schema default.
model = (
    persona.metadata.target_model
    if persona.metadata.target_model not in ("model", "")
    else os.getenv("MODEL", "gpt-4o")
)

llm = ChatOpenAI(
    base_url=base_url,
    api_key=api_key,
    model=model,
    temperature=persona.config.temperature,
    max_tokens=persona.config.max_tokens,
    stop=persona.config.stop,         # may be None – ChatOpenAI handles that gracefully
)

# The persona system prompt is injected as the *first* message in every call.
# Constructing it once avoids repeated string allocations across turns.
_SYSTEM_MESSAGE = SystemMessage(content=persona.prompts.system)


# ── 4. Core agent helper ────────────────────────────────────────────────────────

@traceable(run_type="chain", name="SimulatedAgentRun")
def simulate_agent_run(
    user_input: str,
    history: list[BaseMessage],
    mocked_tool_call: Optional[callable] = None,
    tool_args: Optional[dict] = None,
) -> str:
    """Simulates an LLM chain deciding to use a tool, executing it, and responding.

    Architecture note
    -----------------
    The persona system prompt is always the *first* message so the model never
    loses its role instructions regardless of how long the history grows.
    """
    # System prompt → history → current user turn
    inputs: list[BaseMessage] = [_SYSTEM_MESSAGE] + history + [HumanMessage(content=user_input)]

    llm_response = llm.invoke(inputs)
    final_response: str = llm_response.content

    if mocked_tool_call:
        print(f"\n[Agent Thought] I need to use {mocked_tool_call.name} to answer this.")
        try:
            tool_result = mocked_tool_call.invoke(tool_args)
            print(f"[Agent Tool Output] {tool_result}")

            synthesis_inputs: list[BaseMessage] = inputs + [
                AIMessage(content=f"Tool {mocked_tool_call.name} returned: {tool_result}")
            ]
            llm_response = llm.invoke(synthesis_inputs)
            final_response = llm_response.content
        except Exception as exc:
            final_response = (
                f"I encountered an error while using the tool to fetch your data: {exc}"
            )
            print(f"[Agent Executor Error Caught] {exc}")

    return final_response


# ── 5. Scenarios ────────────────────────────────────────────────────────────────

@traceable(name="Scenario_1_Multi_Turn")
def run_scenario_1() -> None:
    print("\n" + "=" * 50)
    print("Scenario 1: Multi-turn dialogue (5 turns) requiring 3 tool calls")
    print("=" * 50)

    history: list[BaseMessage] = []

    def _turn(msg: str, **kwargs) -> str:
        resp = simulate_agent_run(msg, history, **kwargs)
        history.extend([HumanMessage(content=msg), AIMessage(content=resp)])
        return resp

    print("\nUser: Hi there! Can you help me plan my day?")
    print(f"\nAgent: {_turn('Hi there! Can you help me plan my day?')}")

    print("\nUser: I'm currently in Taipei. Do I need an umbrella today?")
    print(f"\nAgent: {_turn('Do I need an umbrella today?', mocked_tool_call=get_weather, tool_args={'location': 'Taipei'})}")

    print("\nUser: Okay, thanks! I also need to calculate my expenses. I spent 120 on coffee and 250 on lunch.")
    print(f"\nAgent: {_turn('Calculate 120 + 250 for me.', mocked_tool_call=calculate_sum, tool_args={'a': 120, 'b': 250})}")

    print("\nUser: Great. Can you check my user settings? My user ID is 123.")
    print(f"\nAgent: {_turn('User ID is 123.', mocked_tool_call=fetch_user_settings, tool_args={'user_id': '123'})}")

    print("\nUser: Awesome, that's all I needed. Have a good day!")
    print(f"\nAgent: {_turn('Awesome, have a good day!')}")


@traceable(name="Scenario_2_Single_Turn_No_Tools")
def run_scenario_2() -> None:
    print("\n" + "=" * 50)
    print("Scenario 2: Single-turn request (no tools)")
    print("=" * 50)
    user_input = "Write a haiku about programming."
    print(f"\nUser: {user_input}")
    print(f"\nAgent: {simulate_agent_run(user_input, [])}")


@traceable(name="Scenario_3_Single_Turn_One_Tool")
def run_scenario_3() -> None:
    print("\n" + "=" * 50)
    print("Scenario 3: Request requiring a single tool call")
    print("=" * 50)
    user_input = "What is the weather like in Tokyo right now?"
    print(f"\nUser: {user_input}")
    print(f"\nAgent: {simulate_agent_run(user_input, [], mocked_tool_call=get_weather, tool_args={'location': 'Tokyo'})}")


@traceable(name="Scenario_4_Error_Handling")
def run_scenario_4() -> None:
    print("\n" + "=" * 50)
    print("Scenario 4: Intentional tool error / defensive programming test")
    print("=" * 50)
    user_input = "Please fetch user settings for user ID 999."
    print(f"\nUser: {user_input}")
    print(f"\nAgent: {simulate_agent_run(user_input, [], mocked_tool_call=fetch_user_settings, tool_args={'user_id': '999'})}")


@traceable(name="Scenario_5_Parallel_or_Multiple_Tools")
def run_scenario_5() -> None:
    print("\n" + "=" * 50)
    print("Scenario 5: Multiple distinct tool calls in one turn")
    print("=" * 50)
    user_input = "Tell me the weather in Taipei AND Tokyo, then add 5.5 and 2.2."
    print(f"\nUser: {user_input}")

    simulate_agent_run(user_input, [], mocked_tool_call=get_weather,    tool_args={"location": "Taipei"})
    simulate_agent_run(user_input, [], mocked_tool_call=get_weather,    tool_args={"location": "Tokyo"})
    response = simulate_agent_run(user_input, [], mocked_tool_call=calculate_sum, tool_args={"a": 5.5, "b": 2.2})
    print(f"\nAgent: {response}")


# ── Entry-point ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGCHAIN_API_KEY") == "your-api-key":
        print("Warning: LANGCHAIN_API_KEY is not set or is default. Tracing to LangSmith will fail.")

    try:
        run_scenario_1()
        run_scenario_2()
        run_scenario_3()
        run_scenario_4()
        run_scenario_5()
        print("\nAll scenarios executed successfully! Check your LangSmith Dashboard to verify tracing.")
    except Exception as exc:
        print(f"\nAn error occurred during testing: {exc}")
        raise
