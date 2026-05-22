"""
Automated unit and integration tests for the Hacker News Agent.
Uses pytest and FastAPI TestClient.
"""

import json
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from ag_ui.core.types import (
    UserMessage,
    AssistantMessage,
    ToolMessage as AGToolMessage,
    SystemMessage as AGSystemMessage,
    ToolCall as AGToolCall,
    FunctionCall as AGFunctionCall,
    TextInputContent,
)
from hn_agent.server import app, convert_ag_ui_messages_to_langchain
from hn_agent.tools import TOOLS, list_top_stories, get_story_details, fetch_article_content

client = TestClient(app)


def test_root_endpoint() -> None:
    """Verifies that the root HTTP GET endpoint returns online status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "Hacker News" in data["agent"]


def test_capabilities_endpoint() -> None:
    """Verifies that the /capabilities HTTP GET endpoint returns standard capability definitions."""
    response = client.get("/capabilities")
    assert response.status_code == 200
    data = response.json()
    
    # Assert Identity
    assert "identity" in data
    assert data["identity"]["name"] == "Hacker News Summarization Agent"
    assert data["identity"]["type"] == "langgraph"
    
    # Assert Transport
    assert data["transport"]["streaming"] is True
    
    # Assert Tools lists our 3 specialized tools
    tools = data["tools"]["items"]
    tool_names = [t["name"] for t in tools]
    assert "list_top_stories" in tool_names
    assert "get_story_details" in tool_names
    assert "fetch_article_content" in tool_names


def test_message_conversion() -> None:
    """Verifies successful parsing/conversion from AG-UI models to LangChain formats."""
    # 1. Simple User Message
    ag_user_msg = UserMessage(id="msg-1", role="user", content="Hello")
    
    # 2. Multimodal/List-based User Message
    ag_user_multi = UserMessage(
        id="msg-2", 
        role="user", 
        content=[TextInputContent(type="text", text="Hello from list")]
    )
    
    # 3. System Message
    ag_sys_msg = AGSystemMessage(id="msg-3", role="system", content="Act as a summary bot")
    
    # 4. Assistant Message with Tool Calls
    ag_assistant_msg = AssistantMessage(
        id="msg-4",
        role="assistant",
        content="Thinking...",
        toolCalls=[
            AGToolCall(
                id="call-1",
                type="function",
                function=AGFunctionCall(name="list_top_stories", arguments='{"limit": 5}')
            )
        ]
    )
    
    # 5. Tool Result Message
    ag_tool_msg = AGToolMessage(
        id="msg-5",
        role="tool",
        content="Success content",
        toolCallId="call-1"
    )
    
    converted = convert_ag_ui_messages_to_langchain([
        ag_user_msg,
        ag_user_multi,
        ag_sys_msg,
        ag_assistant_msg,
        ag_tool_msg
    ])
    
    assert len(converted) == 5
    
    # Assert types
    assert isinstance(converted[0], HumanMessage)
    assert converted[0].content == "Hello"
    assert converted[0].id == "msg-1"
    
    assert isinstance(converted[1], HumanMessage)
    assert converted[1].content == "Hello from list"
    
    assert isinstance(converted[2], SystemMessage)
    assert converted[2].content == "Act as a summary bot"
    
    assert isinstance(converted[3], AIMessage)
    assert converted[3].content == "Thinking..."
    assert len(converted[3].tool_calls) == 1
    assert converted[3].tool_calls[0]["name"] == "list_top_stories"
    assert converted[3].tool_calls[0]["args"] == {"limit": 5}
    assert converted[3].tool_calls[0]["id"] == "call-1"
    
    assert isinstance(converted[4], ToolMessage)
    assert converted[4].content == "Success content"
    assert converted[4].tool_call_id == "call-1"


def test_tools_meta_structure() -> None:
    """Ensures our LangChain tools are defined with correct default parameters and names."""
    assert len(TOOLS) == 3
    
    # Verify list_top_stories
    assert list_top_stories.name == "list_top_stories"
    assert "limit" in list_top_stories.args
    
    # Verify get_story_details
    assert get_story_details.name == "get_story_details"
    assert "story_id" in get_story_details.args
    assert "max_comments" in get_story_details.args
    
    # Verify fetch_article_content
    assert fetch_article_content.name == "fetch_article_content"
    assert "url" in fetch_article_content.args
