"""
LangChain tools wrapping dynamic Hacker News MCP server tools.
Employs ContextVars to securely share the active MCP ClientSession and dynamic tools.
"""

import asyncio
from contextvars import ContextVar
import logging
from typing import Any, Dict, List, Optional, Type

from langchain_core.messages import ToolMessage as LCToolMessage
from langchain_core.tools import StructuredTool
from mcp import ClientSession
from mcp.types import Tool
import pydantic

# Configure logger
logger = logging.getLogger("hn_agent.tools")

# ContextVar to hold the active ClientSession for the duration of a run
mcp_session_var: ContextVar[Optional[ClientSession]] = ContextVar("mcp_session", default=None)

# Type mapping for JSON schema types to Python types
TYPE_MAP: Dict[str, Type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def json_schema_to_pydantic(name: str, schema: dict) -> Type[pydantic.BaseModel]:
    """
    Converts a JSON schema from MCP tool inputSchema to a Pydantic BaseModel.
    """
    fields = {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for field_name, prop in properties.items():
        field_type_str = prop.get("type", "string")
        field_type = TYPE_MAP.get(field_type_str, Any)

        description = prop.get("description", "")
        # For required fields, use ... (Ellipsis), otherwise use the default value or None
        if field_name in required:
            default = ...
        else:
            default = prop.get("default", None)

        fields[field_name] = (field_type, pydantic.Field(default=default, description=description))

    return pydantic.create_model(name, **fields)


def create_mcp_tool_wrapper(tool_name: str, schema: dict) -> StructuredTool:
    """
    Wraps an MCP tool dynamically in a LangChain StructuredTool.
    Executes the tool through the active ClientSession in the context variable.
    """
    async def _arun(**kwargs) -> str:
        session = mcp_session_var.get()
        if session is None:
            return "Error: MCP session is not active or initialized."
        try:
            result = await session.call_tool(tool_name, kwargs)
            
            # Extract and concatenate all text block contents from the response
            text_blocks = []
            for block in result.content:
                if hasattr(block, "text") and block.text:
                    text_blocks.append(block.text)
                elif isinstance(block, dict) and block.get("type") == "text":
                    text_blocks.append(block.get("text", ""))
                    
            # Dynamically detect if multiple JSON blocks are returned (e.g. from a list of objects)
            # and wrap them inside a proper single JSON array.
            if len(text_blocks) > 1:
                parsed_blocks = []
                all_parsed = True
                for tb in text_blocks:
                    tb_stripped = tb.strip()
                    if (tb_stripped.startswith("{") and tb_stripped.endswith("}")) or (tb_stripped.startswith("[") and tb_stripped.endswith("]")):
                        try:
                            import json
                            parsed_blocks.append(json.loads(tb_stripped))
                        except Exception:
                            all_parsed = False
                            break
                    else:
                        all_parsed = False
                        break
                
                if all_parsed:
                    import json
                    return json.dumps(parsed_blocks)
                    
            return "".join(text_blocks)
        except Exception as e:
            return f"Error calling {tool_name}: {e}"

    pydantic_model = json_schema_to_pydantic(tool_name, schema)

    return StructuredTool.from_function(
        coroutine=_arun,
        name=tool_name,
        description=schema.get("description") or f"Call tool {tool_name} on the MCP server.",
        args_schema=pydantic_model
    )


def build_dynamic_tools(mcp_tools: List[Any]) -> List[StructuredTool]:
    """
    Converts a list of MCP Tool models into a list of LangChain StructuredTools.
    """
    tools = []
    for tool in mcp_tools:
        # tool could be an instance of mcp.types.Tool or a dict
        if isinstance(tool, dict):
            name = tool.get("name")
            schema = {
                "description": tool.get("description", ""),
                "properties": tool.get("inputSchema", {}).get("properties", {}),
                "required": tool.get("inputSchema", {}).get("required", []),
            }
        else:
            name = getattr(tool, "name", "")
            input_schema = getattr(tool, "inputSchema", {}) or {}
            schema = {
                "description": getattr(tool, "description", "") or "",
                "properties": input_schema.get("properties", {}),
                "required": input_schema.get("required", []),
            }
        tools.append(create_mcp_tool_wrapper(name, schema))
    return tools


# Fallback/default tools metadata representing the 3 Hacker News tools.
# Ensures capabilities endpoint is always responsive and tests pass offline.
FALLBACK_TOOLS_METADATA: List[Dict[str, Any]] = [
    {
        "name": "list_top_stories",
        "description": "List the current top Hacker News stories from the front page.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "The maximum number of stories to fetch (default: 30, max: 50)."
                }
            }
        }
    },
    {
        "name": "get_story_details",
        "description": "Fetch the details of a specific Hacker News story, including metadata and top comments.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "story_id": {
                    "type": "integer",
                    "description": "The Hacker News story ID."
                },
                "max_comments": {
                    "type": "integer",
                    "description": "The maximum number of top-level comments to include (default: 5, max: 20)."
                }
            },
            "required": ["story_id"]
        }
    },
    {
        "name": "fetch_article_content",
        "description": "Fetch and extract the readable main-body text of any URL/article linked in Hacker News stories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The article URL to fetch."
                }
            },
            "required": ["url"]
        }
    }
]

# Generate default/fallback tools
FALLBACK_TOOLS = build_dynamic_tools(FALLBACK_TOOLS_METADATA)

# Re-expose individual tools and the static/default list for backward compatibility in tests
TOOLS = FALLBACK_TOOLS
list_top_stories = FALLBACK_TOOLS[0]
get_story_details = FALLBACK_TOOLS[1]
fetch_article_content = FALLBACK_TOOLS[2]

# ContextVar to hold the active dynamic tools for the duration of a run
# Defaults to the statically initialized FALLBACK_TOOLS list
mcp_tools_var: ContextVar[List[StructuredTool]] = ContextVar("mcp_tools", default=FALLBACK_TOOLS)


async def get_mcp_tools_metadata() -> List[Dict[str, Any]]:
    """
    Attempts to connect to the MCP server and fetch live tool metadata dynamically.
    If the connection fails or times out, seamlessly falls back to FALLBACK_TOOLS_METADATA.
    """
    try:
        from mcp.client.sse import sse_client
        from hn_agent import config
        
        async with sse_client(config.HN_MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                # Perform rapid handshake and fetch tools list
                await asyncio.wait_for(session.initialize(), timeout=3.0)
                mcp_tools_result = await asyncio.wait_for(session.list_tools(), timeout=3.0)
                
                metadata_list = []
                for tool in mcp_tools_result.tools:
                    metadata_list.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": tool.inputSchema
                    })
                return metadata_list
    except Exception as e:
        logger.warning(f"Could not connect to live MCP server to fetch capabilities ({e}). Using fallback tool metadata.")
        return FALLBACK_TOOLS_METADATA


async def execute_tools(state: Any) -> Dict[str, List[LCToolMessage]]:
    """
    Custom LangGraph execution node. Dynamically executes requested tools in parallel
    using the active tools list in mcp_tools_var.
    """
    messages = state["messages"]
    last_message = messages[-1]

    # Get active tools for this context (falls back to FALLBACK_TOOLS if not set)
    tools = mcp_tools_var.get()
    tools_by_name = {t.name: t for t in tools}

    async def run_one_tool(tool_call: Dict[str, Any]) -> LCToolMessage:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]

        if tool_name in tools_by_name:
            tool_obj = tools_by_name[tool_name]
            try:
                result = await tool_obj.ainvoke(tool_args)
                content_str = str(result)
                if hasattr(result, "content"):
                    content_str = result.content
                return LCToolMessage(
                    content=content_str,
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
            except Exception as e:
                return LCToolMessage(
                    content=f"Error executing tool {tool_name}: {e}",
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
        else:
            return LCToolMessage(
                content=f"Error: Tool '{tool_name}' not found.",
                tool_call_id=tool_call_id,
                name=tool_name
            )

    # Execute all tool calls in parallel using gather
    tool_messages = await asyncio.gather(*(run_one_tool(tc) for tc in last_message.tool_calls))
    return {"messages": list(tool_messages)}
