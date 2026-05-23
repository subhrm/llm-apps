import React, { useState, useEffect, useMemo, useRef } from "react";
import { HttpAgent, randomUUID, type Message } from "@ag-ui/client";
import type { HNStory, ActiveToolCall } from "./types/HNTypes";
import { parseMarkdown } from "./utils/markdown";

function App() {
  const [messages, setMessages] = useState<ReadonlyArray<Message>>([]);
  const [stories, setStories] = useState<HNStory[]>([]);
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [isLoadingStories, setIsLoadingStories] = useState(false);
  const [activeTool, setActiveTool] = useState<ActiveToolCall | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [serverOnline, setServerOnline] = useState(true);

  const viewportRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLTextAreaElement>(null);

  // Helper to extract the result content of a specific tool call from the message history
  const findToolResult = (toolCallId: string): string | undefined => {
    const toolMsg = messages.find(m => m.role === "tool" && (m as any).toolCallId === toolCallId);
    return toolMsg?.content ? String(toolMsg.content) : undefined;
  };

  // Initialize HttpAgent to connect to our local server
  const agent = useMemo(() => {
    return new HttpAgent({
      url: "http://127.0.0.1:8001/chat",
      threadId: `hn-session-${Date.now()}`,
      initialMessages: [],
    });
  }, []);

  // Check agent server capability on mount
  useEffect(() => {
    fetch("http://127.0.0.1:8001/capabilities")
      .then((res) => {
        if (res.ok) setServerOnline(true);
        else setServerOnline(false);
      })
      .catch(() => setServerOnline(false));
  }, []);

  // Synchronize state with HttpAgent message updates
  useEffect(() => {
    const subscription = agent.subscribe({
      onMessagesChanged({ messages: updatedMessages }) {
        setMessages([...updatedMessages]);
        // Auto-scroll chat to bottom
        setTimeout(() => {
          if (viewportRef.current) {
            viewportRef.current.scrollTop = viewportRef.current.scrollHeight;
          }
        }, 80);
      },
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [agent]);

  // Adjust input textarea height dynamically
  useEffect(() => {
    if (chatInputRef.current) {
      chatInputRef.current.style.height = "24px";
      chatInputRef.current.style.height = `${Math.min(chatInputRef.current.scrollHeight - 16, 120)}px`;
    }
  }, [chatInput]);

  // General function to trigger an Agent execution with active subscribers
  const triggerAgentRun = async (userPrompt: string, quiet: boolean = false) => {
    if (isAgentRunning) return;
    setIsAgentRunning(true);
    setActiveTool(null);

    // Add user message to history
    agent.addMessage({
      id: randomUUID(),
      role: "user",
      content: userPrompt,
    });

    try {
      let runActiveTool: ActiveToolCall | null = null;

      await agent.runAgent(
        {},
        {
          onToolCallStartEvent({ event }) {
            const tc = {
              id: event.toolCallId,
              name: event.toolCallName,
              args: "",
              finished: false,
            };
            runActiveTool = tc;
            setActiveTool(tc);
          },
          onToolCallArgsEvent({ event, toolCallBuffer }) {
            if (runActiveTool && runActiveTool.id === event.toolCallId) {
              const updatedArgs = toolCallBuffer || runActiveTool.args + event.delta;
              runActiveTool.args = updatedArgs;
              setActiveTool({ ...runActiveTool });
            }
          },
          onToolCallEndEvent({ event }) {
            if (runActiveTool && runActiveTool.id === event.toolCallId) {
              runActiveTool.finished = true;
              setActiveTool({ ...runActiveTool });
            }
          },
          onToolCallResultEvent({ event }) {
            // Check if this tool fetched stories list and hydrate our dashboard
            if (runActiveTool && runActiveTool.name === "list_top_stories") {
              try {
                const parsed = JSON.parse(event.content);
                if (Array.isArray(parsed)) {
                  setStories(parsed);
                }
              } catch (e) {
                console.error("Failed to parse stories JSON:", e);
              }
            }
            runActiveTool = null;
            setActiveTool(null);
          },
          onRunFinishedEvent() {
            setIsAgentRunning(false);
            setActiveTool(null);
            if (quiet) {
              setIsLoadingStories(false);
            }
          },
          onRunErrorEvent() {
            setIsAgentRunning(false);
            setActiveTool(null);
            if (quiet) {
              setIsLoadingStories(false);
            }
          },
          onRunFailed() {
            setIsAgentRunning(false);
            setActiveTool(null);
            if (quiet) {
              setIsLoadingStories(false);
            }
          },
        }
      );
    } catch (err) {
      console.error("Error executing agent loop:", err);
      setIsAgentRunning(false);
      setActiveTool(null);
      setIsLoadingStories(false);
    }
  };

  // Click handler to load top Hacker News stories
  const handleLoadStories = async () => {
    if (isAgentRunning || isLoadingStories) return;
    setIsLoadingStories(true);
    setStories([]);
    // Run quiet command to agent to let it invoke the list_top_stories tool
    await triggerAgentRun("Please fetch the top 15 stories from the homepage.", false);
    setIsLoadingStories(false);
  };

  // Click handler to summarize story comments
  const handleSummarizeStory = (story: HNStory) => {
    const prompt = `Please fetch details and summarize the top comments for the story: "${story.title}" (ID: ${story.id})`;
    triggerAgentRun(prompt);
  };

  // Click handler to scrape external article and summarize it
  const handleSummarizeArticle = (story: HNStory) => {
    if (!story.url) return;
    const prompt = `Please scrape the article body content and summarize this story: "${story.title}" linking to ${story.url}`;
    triggerAgentRun(prompt);
  };

  // Textarea input send handler
  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isAgentRunning) return;
    const text = chatInput.trim();
    setChatInput("");
    triggerAgentRun(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  return (
    <div className="app-container">
      {/* LEFT SIDEBAR: Hacker News Stories Dashboard */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand-wrapper">
            <div className="logo-icon">Y</div>
            <h1 className="brand-title">Hacker News AI</h1>
          </div>
          
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span className={`server-status ${serverOnline ? "status-online" : "status-offline"}`}>
              <span className="status-dot"></span>
              {serverOnline ? "Agent Online" : "Agent Offline"}
            </span>
          </div>

          <button 
            className="refresh-btn" 
            onClick={handleLoadStories}
            disabled={isAgentRunning || isLoadingStories}
          >
            {isLoadingStories ? (
              <>
                <span className="spinner orange-spinner" style={{ width: "14px", height: "14px" }}></span>
                Loading Board...
              </>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                </svg>
                Load Live Board
              </>
            )}
          </button>
        </div>

        {/* Stories deck cards */}
        <div className="stories-deck">
          {stories.length > 0 ? (
            stories.map((story) => (
              <div className="story-card" key={story.id}>
                <a 
                  href={story.hn_url || `https://news.ycombinator.com/item?id=${story.id}`} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="story-title"
                >
                  {story.title}
                </a>
                
                <div className="story-meta">
                  <span className="score-badge">{story.score} pts</span>
                  <span className="comments-badge">{story.descendants || 0} comments</span>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>by {story.by}</span>
                </div>

                <div className="story-actions">
                  <button 
                    className="action-sub-btn" 
                    onClick={() => handleSummarizeStory(story)}
                    disabled={isAgentRunning}
                  >
                    💬 Summary
                  </button>
                  {story.url ? (
                    <button 
                      className="action-sub-btn" 
                      onClick={() => handleSummarizeArticle(story)}
                      disabled={isAgentRunning}
                    >
                      🔗 Read Link
                    </button>
                  ) : (
                    <button className="action-sub-btn" disabled style={{ opacity: 0.3, cursor: "not-allowed" }}>
                      No Link
                    </button>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="loading-deck-placeholder">
              {isLoadingStories ? (
                <>
                  <span className="spinner" style={{ width: "32px", height: "32px" }}></span>
                  <p style={{ fontSize: "14px" }}>Fetching live front page stories...</p>
                </>
              ) : (
                <>
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ opacity: 0.4 }}>
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                  <p style={{ fontSize: "14px" }}>No stories loaded.</p>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", maxWidth: "220px" }}>Click "Load Live Board" above to scrape the Hacker News frontpage.</p>
                </>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* RIGHT WORKSPACE: Chat Console */}
      <main className="workspace">
        {/* Workspace Header */}
        <header className="workspace-header">
          <div className="workspace-details">
            <div className="agent-name-main">Hacker News Summary Assistant</div>
            <div className="agent-desc-main">Stateful Agent ReAct Loop Console</div>
          </div>

          <div className="capabilities-chip">
            <span className="cap-badge">LangGraph</span>
            <span className="cap-badge">FastMCP SSE</span>
            <span className="cap-badge">AG-UI</span>
          </div>
        </header>

        {/* Chat message history viewport */}
        <div className="chat-viewport" ref={viewportRef}>
          {messages.length === 0 ? (
            <div className="welcome-splash">
              <div className="splash-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <h2 className="splash-title">Hacker News Summary Agent</h2>
              <p className="splash-desc">
                Welcome! I am an AI Agent powered by **LangGraph** and linked directly to a Hacker News SSE MCP backend. 
                I can list stories, crawl linked website articles, extract readable text, and write concise summaries of top discussions.
              </p>

              <div className="splash-suggestions">
                <button 
                  className="suggestion-card" 
                  onClick={() => triggerAgentRun("List the top 5 stories on Hacker News and summarize their details.")}
                  disabled={isAgentRunning}
                >
                  🚀 "List the top 5 stories on Hacker News and summarize details"
                </button>
                <button 
                  className="suggestion-card" 
                  onClick={() => triggerAgentRun("Summarize the current top discussion thread on Hacker News.")}
                  disabled={isAgentRunning}
                >
                  💬 "Summarize the current top discussion thread"
                </button>
              </div>
            </div>
          ) : (
            messages
              .filter(m => m.role === "user" || (m.role === "assistant" && (m.content || m.toolCalls)))
              .map((msg) => {
                const isUser = msg.role === "user";
                let textContent = "";
                if (typeof msg.content === "string") {
                  textContent = msg.content;
                } else if (Array.isArray(msg.content)) {
                  textContent = (msg.content as any[])
                    .map((part: any) => (part && typeof part === "object" && "text" in part ? String(part.text) : ""))
                    .join("");
                }

                return (
                  <div className={`message-row ${isUser ? "user" : "assistant"}`} key={msg.id}>
                    <div className="bubble">
                      {isUser ? (
                        <p style={{ margin: 0 }}>{textContent}</p>
                      ) : (
                        <>
                          {textContent && (
                            <div 
                              dangerouslySetInnerHTML={{ 
                                __html: parseMarkdown(textContent) 
                              }} 
                            />
                          )}
                          {msg.toolCalls && msg.toolCalls.length > 0 && (
                            <div className="agent-steps-accordion">
                              <details className="steps-details">
                                <summary className="steps-summary">
                                  <span className="steps-summary-title">
                                    Agent Thought Process ({msg.toolCalls.length} step{msg.toolCalls.length > 1 ? "s" : ""})
                                  </span>
                                </summary>
                                <div className="steps-content">
                                  {msg.toolCalls.map((tc: any) => {
                                    const result = findToolResult(tc.id);
                                    return (
                                      <div key={tc.id} className="step-item">
                                        <div className="step-header">
                                          <span className="step-icon">⚙️</span>
                                          <span className="step-name">{tc.function.name}</span>
                                          <span className={`step-status ${result ? "status-success" : "status-running"}`}>
                                            {result ? "completed" : "running..."}
                                          </span>
                                        </div>
                                        <div className="step-details-box">
                                          <div className="step-args">
                                            <strong>Arguments:</strong> <code>{tc.function.arguments}</code>
                                          </div>
                                          {result && (
                                            <div className="step-result">
                                              <strong>Result:</strong>
                                              <pre className="step-result-pre">{result}</pre>
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </details>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                );
              })
          )}
        </div>

        {/* ACTIVE THINKING LOGGER */}
        {activeTool && (
          <div className="thinking-block">
            <div className="thinking-header">
              <span className="spinner" style={{ width: "14px", height: "14px" }}></span>
              <span>AGENT THOUGHT PROCESS</span>
            </div>
            <div className="active-tool-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
              </svg>
              Calling Tool: {activeTool.name}
            </div>
            {activeTool.args && (
              <div className="tool-arguments">
                <strong>Arguments:</strong> {activeTool.args}
              </div>
            )}
          </div>
        )}

        {/* INPUT CONSOLE BAR */}
        <div className="input-console">
          <form onSubmit={handleSendMessage} style={{ margin: 0 }}>
            <div className="input-bar-wrapper">
              <textarea
                ref={chatInputRef}
                className="chat-textarea"
                placeholder="Ask the Agent a custom question..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isAgentRunning}
              />
              <button 
                type="submit" 
                className="send-btn" 
                disabled={!chatInput.trim() || isAgentRunning}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>
          </form>
          <div className="console-tip">
            Press Enter to Send, Shift + Enter for a new line.
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
