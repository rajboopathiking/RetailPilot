# from models.db_model import MessageState
# from utils.tools import get_columns_list,get_details,invoice_generator,sales_agent_tool,support_agent_tool
# from agent.llm_models import groq_llm



# tools = [
#     sales_agent_tool,
#     support_agent_tool,
# ]



# llm = groq_llm

# tools_map = {tool.name : tool for tool in tools}

# llm_w_tools = llm.bind_tools(tools=tools)

# from langgraph.graph import StateGraph, START, END
# from langchain_core.messages import (
#     AIMessage,
#     ToolMessage,
# )

# from prompts.prompt import system_prompt

# from langgraph.checkpoint.memory import InMemorySaver
# from langgraph.prebuilt import tools_condition,ToolNode

# # Bind tools to the LLM
# llm_w_tools = llm.bind_tools(tools)


# system_prompt = system_prompt.invoke({
#     "instruction": "Be concise."}).to_messages()

# async def llm_node(state: MessageState):
#     response = await llm_w_tools.ainvoke([
#         *system_prompt,
#         *state["messages"]
#     ])

#     print("Tool calls:", response.tool_calls)

#     return {"messages": [response]}


# # 2. Tool Node
# async def toolNode(state: MessageState):
#     """Execute tools requested by the LLM."""

#     message = state["messages"][-1]
#     results = []

#     for tool_call in message.tool_calls:
#         selected_tool = tools_map[tool_call["name"]]

#         result = await selected_tool.ainvoke(
#             tool_call["args"]
#         )

        

#         results.append(
#             ToolMessage(
#                 content=str(result),
#                 tool_call_id=tool_call["id"],
#                 name=tool_call["name"]
#             )
#         )

#     return {
#         "messages": results
#     }


# # 3. Conditional Routing
# def tool_conditions(state: MessageState):
#     """Determine whether the LLM requested tools."""

#     last_message = state["messages"][-1]

#     if isinstance(last_message, AIMessage) and last_message.tool_calls:
#         return "tools_node"

#     return END


# # 4. Build Graph
# graph = StateGraph(MessageState)

# graph.add_node("llm_node", llm_node)
# graph.add_node("tools_node", ToolNode(tools=tools, handle_tool_errors=True))

# graph.add_edge(START, "llm_node")

# # graph.add_conditional_edges(
# #     "llm_node",
# #     tools_condition,
# #     {
# #         "tools_node": "tools_node",
# #         END: END
# #     }
# # )


# graph.add_conditional_edges(
#     "llm_node",
#     tools_condition,
#     {
#         "tools": "tools_node",
#         "__end__": END
#     }
# )

# graph.add_edge("tools_node", "llm_node")

# app = graph.compile(checkpointer=InMemorySaver())


import json
import logging

from models.db_model import MessageState
from utils.tools import sales_agent_tool, support_agent_tool
from agent.llm_models import groq_llm, google_llm, get_active_llm
from prompts.prompt import system_prompt

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from langgraph.prebuilt import ToolNode,tools_condition

from langchain_core.messages import (
    AIMessage,
    ToolMessage,
)

logger = logging.getLogger(__name__)

tools = [sales_agent_tool, support_agent_tool]
tools_map = {tool.name: tool for tool in tools}

active_llm = get_active_llm()
llm_w_tools = active_llm.bind_tools(tools)

prompt_messages = system_prompt.invoke({
    "instruction": (
        "Be concise. Delegate only when necessary. "
        "For greetings, respond directly without tools."
    )
}).to_messages()

async def llm_node(state: MessageState):
    # Dynamically resolve active LLM in case key was updated from UI at runtime
    bound_llm = get_active_llm().bind_tools(tools)
    response = await bound_llm.ainvoke([
        *prompt_messages,
        *state["messages"],
    ])

    print("Tool calls:", response.tool_calls)

    return {"messages": [response]}


def tool_conditions(state: MessageState):
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools_node"

    return END


def normalize_result(result):
    if result is None or result == []:
        return "No information found."

    if isinstance(result, str):
        return result or "No information found."

    return json.dumps(result, default=str)


async def tool_node(state: MessageState):
    message = state["messages"][-1]
    tool_calls = message.tool_calls

    results = []
    final_answer = "No information found."

    for index, tool_call in enumerate(tool_calls):
        name = tool_call["name"]

        if index > 0:
            content = "Skipped: only one delegation allowed."
        else:
            try:
                selected_tool = tools_map[name]
                result = await selected_tool.ainvoke(
                    tool_call["args"]
                )
                content = normalize_result(result)

            except Exception:
                logger.exception("Agent tool failed")
                content = "Unable to complete the request."

            final_answer = content

        results.append(
            ToolMessage(
                content=content,
                tool_call_id=tool_call["id"],
                name=name,
            )
        )

    return {
        "messages": [
            *results,
            AIMessage(content=final_answer),
        ]
    }


graph = StateGraph(MessageState)

graph.add_node("llm_node", llm_node)
graph.add_node("tools_node", ToolNode(tools))

graph.add_edge(START, "llm_node")

graph.add_conditional_edges(
    "llm_node",
    tools_condition,
    {
        "tools": "tools_node",
        "__end__": END,
    },
)

graph.add_edge("tools_node", END)

app = graph.compile(checkpointer=InMemorySaver())

