"""
FastAPI SSE Server hosting the Hacker News Agent.
Implements the AG-UI (Agent-User Interaction) protocol.
Connects dynamically to the Hacker News MCP server over SSE on each chat request.
"""

import json
import logging
import uuid
from typing import Any, AsyncGenerator, List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from mcp.client.sse import sse_client
from mcp import ClientSession

from ag_ui.core.events import (
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
)
from ag_ui.core.capabilities import (
    AgentCapabilities,
    IdentityCapabilities,
    TransportCapabilities,
    ToolsCapabilities,
    StateCapabilities,
    ExecutionCapabilities,
)
from ag_ui.core.types import Tool as AGTool, RunAgentInput, Message
from ag_ui.encoder.encoder import EventEncoder
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage as LCSystemMessage,
    ToolMessage as LCToolMessage,
)

from hn_agent import config
from hn_agent.agent import agent_app
from hn_agent.tools import mcp_session_var, mcp_tools_var

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hn_agent.server")

app = FastAPI(
    title="Hacker News Agent SSE Server (AG-UI)",
    description="A stateful summarization agent wrapping Hacker News MCP SSE tools and serving AG-UI clients.",
    version="0.1.0"
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def convert_ag_ui_messages_to_langchain(messages: List[Message]) -> List[BaseMessage]:
    """
    Translates ag-ui-protocol Pydantic Message models to standard LangChain messages.
    """
    lc_messages = []
    for msg in messages:
        # 1. User Message
        if msg.role == "user":
            content = msg.content
            if isinstance(content, list):
                text_content = ""
                for part in content:
                    if getattr(part, "type", "") == "text" and hasattr(part, "text"):
                        text_content += part.text
                lc_messages.append(HumanMessage(content=text_content, id=msg.id))
            else:
                lc_messages.append(HumanMessage(content=str(content), id=msg.id))

        # 2. Assistant Message
        elif msg.role == "assistant":
            tool_calls = []
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    # Convert arguments back to a dictionary if stringified
                    tc_args = tc.function.arguments
                    if isinstance(tc_args, str):
                        try:
                            tc_args = json.loads(tc_args)
                        except json.JSONDecodeError:
                            pass
                    tool_calls.append({
                        "name": tc.function.name,
                        "args": tc_args,
                        "id": tc.id,
                        "type": "tool_call"
                    })
            lc_messages.append(AIMessage(content=msg.content or "", tool_calls=tool_calls, id=msg.id))

        # 3. Tool Result Message
        elif msg.role == "tool":
            lc_messages.append(LCToolMessage(
                content=msg.content or "",
                tool_call_id=getattr(msg, "tool_call_id", ""),
                id=msg.id
            ))

        # 4. System Message
        elif msg.role == "system":
            lc_messages.append(LCSystemMessage(content=msg.content or "", id=msg.id))

    return lc_messages


async def run_agent_generator(input_data: RunAgentInput) -> AsyncGenerator[str, None]:
    """
    Asynchronous generator executing LangGraph and yielding AG-UI events encoded as SSE.
    """
    encoder = EventEncoder()
    thread_id = input_data.thread_id
    run_id = input_data.run_id

    # 1. Emit Run Started event
    run_started = RunStartedEvent(
        thread_id=thread_id,
        run_id=run_id,
        parent_run_id=input_data.parent_run_id,
        input=input_data
    )
    yield encoder.encode(run_started)

    # Convert AG-UI messages to LangChain format
    try:
        lc_messages = convert_ag_ui_messages_to_langchain(input_data.messages)
    except Exception as e:
        logger.error(f"Failed to convert messages: {e}")
        yield encoder.encode(RunErrorEvent(message=f"Failed to parse messages: {e}"))
        return

    # Track assistant stream and active tool calls
    assistant_msg_id = str(uuid.uuid4())
    assistant_started = False
    active_tool_calls = {}  # index -> {id, name, args, run_id}

    logger.info(f"Connecting to Hacker News MCP server at {config.HN_MCP_URL}")

    try:
        # Establish connection to MCP server
        async with sse_client(config.HN_MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                # Handshake
                await session.initialize()
                logger.info("Successfully connected and initialized Hacker News MCP session.")

                # Set ContextVar so our tools can make calls
                token = mcp_session_var.set(session)

                # Fetch and bind dynamic tools for this session
                from hn_agent.tools import build_dynamic_tools, TOOLS as FALLBACK_TOOLS
                try:
                    mcp_tools_result = await session.list_tools()
                    dynamic_tools = build_dynamic_tools(mcp_tools_result.tools)
                except Exception as e:
                    logger.warning(f"Failed to fetch live tools from MCP session ({e}). Using fallback tools.")
                    dynamic_tools = FALLBACK_TOOLS
                
                tools_token = mcp_tools_var.set(dynamic_tools)

                try:
                    # Execute LangGraph streaming events
                    async for event in agent_app.astream_events({"messages": lc_messages}, version="v2"):
                        kind = event["event"]

                        # A. Streaming LLM Outputs (text and tool call chunks)
                        if kind == "on_chat_model_stream":
                            chunk = event["data"]["chunk"]

                            # If text tokens are returned
                            if chunk.content:
                                if not assistant_started:
                                    yield encoder.encode(TextMessageStartEvent(
                                        message_id=assistant_msg_id,
                                        role="assistant"
                                    ))
                                    assistant_started = True
                                yield encoder.encode(TextMessageContentEvent(
                                    message_id=assistant_msg_id,
                                    delta=chunk.content
                                ))

                            # If tool call chunks are streamed
                            if chunk.tool_call_chunks:
                                for tc_chunk in chunk.tool_call_chunks:
                                    idx = tc_chunk.get("index")
                                    tc_id = tc_chunk.get("id")
                                    tc_name = tc_chunk.get("name")
                                    tc_args = tc_chunk.get("args")

                                    # If a new tool call chunk starts
                                    if idx not in active_tool_calls and tc_id:
                                        active_tool_calls[idx] = {
                                            "id": tc_id,
                                            "name": tc_name,
                                            "args": ""
                                        }
                                        yield encoder.encode(ToolCallStartEvent(
                                            tool_call_id=tc_id,
                                            tool_call_name=tc_name,
                                            parent_message_id=assistant_msg_id
                                        ))

                                    # Append tool arguments
                                    if idx in active_tool_calls and tc_args:
                                        active_tool_calls[idx]["args"] += tc_args
                                        yield encoder.encode(ToolCallArgsEvent(
                                            tool_call_id=active_tool_calls[idx]["id"],
                                            delta=tc_args
                                        ))

                        # B. Chat Model Generation Ends
                        elif kind == "on_chat_model_end":
                            if assistant_started:
                                yield encoder.encode(TextMessageEndEvent(message_id=assistant_msg_id))
                                assistant_started = False

                            # Signal the end of any active tool calls
                            for idx, tc in list(active_tool_calls.items()):
                                yield encoder.encode(ToolCallEndEvent(tool_call_id=tc["id"]))

                        # C. LangChain Tool Invocation Starts
                        elif kind == "on_tool_start":
                            tool_name = event["name"]
                            run_id_val = event["run_id"]

                            # Bind the run_id to the matching active tool call name
                            for idx, tc in active_tool_calls.items():
                                if tc["name"] == tool_name and "run_id" not in tc:
                                    tc["run_id"] = run_id_val
                                    break

                        # D. LangChain Tool Invocation Completes
                        elif kind == "on_tool_end":
                            tool_name = event["name"]
                            tool_output = event["data"].get("output")
                            run_id_val = event["run_id"]

                            tool_call_id = None
                            for idx, tc in active_tool_calls.items():
                                if tc.get("run_id") == run_id_val:
                                    tool_call_id = tc["id"]
                                    break

                            # Fallback lookup by name if run_id didn't match
                            if not tool_call_id:
                                for idx, tc in active_tool_calls.items():
                                    if tc["name"] == tool_name:
                                        tool_call_id = tc["id"]
                                        break

                            if tool_call_id:
                                # Stringify tool output
                                content_str = str(tool_output)
                                if hasattr(tool_output, "content"):
                                    content_str = tool_output.content

                                yield encoder.encode(ToolCallResultEvent(
                                    message_id=str(uuid.uuid4()),
                                    tool_call_id=tool_call_id,
                                    content=content_str,
                                    role="tool"
                                ))

                                # Delete call from active calls list
                                for idx, tc in list(active_tool_calls.items()):
                                    if tc["id"] == tool_call_id:
                                        del active_tool_calls[idx]

                finally:
                    # Securely reset context vars
                    mcp_session_var.reset(token)
                    mcp_tools_var.reset(tools_token)

        # 4. Emit Run Finished event
        yield encoder.encode(RunFinishedEvent(
            thread_id=thread_id,
            run_id=run_id,
            result={"status": "success"}
        ))

    except Exception as e:
        logger.error(f"Error executing agent loop: {e}", exc_info=True)
        yield encoder.encode(RunErrorEvent(message=f"Error executing agent loop: {e}"))


# Expose standard AG-UI Chat/Runs Endpoints
@app.post("/chat")
@app.post("/runs")
@app.post("/agent")
async def chat(input_data: RunAgentInput):
    """
    Primary endpoint that accepts RunAgentInput and yields AG-UI events via HTTP SSE.
    """
    return StreamingResponse(
        run_agent_generator(input_data),
        media_type="text/event-stream"
    )


# Expose standard AG-UI GET Capabilities Endpoint
@app.get("/capabilities")
@app.get("/capabilities/")
async def get_capabilities() -> AgentCapabilities:
    """
    Returns standard capabilities defining Hacker News Agent tools, state, and identity.
    """
    from hn_agent.tools import get_mcp_tools_metadata
    metadata_list = await get_mcp_tools_metadata()

    ag_tools = []
    for tool_meta in metadata_list:
        ag_tools.append(
            AGTool(
                name=tool_meta["name"],
                description=tool_meta.get("description", ""),
                parameters=tool_meta.get("inputSchema", {})
            )
        )

    return AgentCapabilities(
        identity=IdentityCapabilities(
            name="Hacker News Summarization Agent",
            type="langgraph",
            description="An AI agent powered by LangGraph that browses Hacker News and summarizes stories and articles using custom MCP tools.",
            version="0.1.0"
        ),
        transport=TransportCapabilities(
            streaming=True
        ),
        tools=ToolsCapabilities(
            supported=True,
            items=ag_tools
        ),
        state=StateCapabilities(
            snapshots=True,
            persistent_state=True
        ),
        execution=ExecutionCapabilities(
            max_iterations=12
        )
    )


@app.get("/")
async def root():
    """Welcome and status check endpoint."""
    return {
        "status": "online",
        "agent": "Hacker News Summarization Agent",
        "protocol": "ag-ui-protocol",
        "endpoints": {
            "chat": "POST /chat",
            "runs": "POST /runs",
            "agent": "POST /agent",
            "capabilities": "GET /capabilities"
        }
    }
