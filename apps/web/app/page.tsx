"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useEffect, useMemo, useState } from "react";

type SessionRecord = {
  id: string;
  title: string;
  created_at: string;
};

type GatewayEvent = {
  id: string;
  session_id: string;
  type: string;
  message: string;
  agent_name: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

type MemoryRecord = {
  id: string;
  session_id: string;
  role: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

type MaterialIconName =
  | "add"
  | "auto_awesome"
  | "bolt"
  | "chat_bubble"
  | "check_circle"
  | "chevron_right"
  | "close"
  | "database"
  | "description"
  | "dns"
  | "history"
  | "keyboard_command_key"
  | "memory"
  | "monitoring"
  | "more_horiz"
  | "psychology"
  | "radio_button_checked"
  | "refresh"
  | "schedule"
  | "search"
  | "send"
  | "smart_toy"
  | "stacks"
  | "terminal";

/** Renders a Google Material Symbols icon with consistent sizing in the dashboard UI. */
function MaterialIcon({ name, size = 18 }: { name: MaterialIconName; size?: number }) {
  return (
    <span
      aria-hidden="true"
      className="material-symbols-outlined material-icon"
      style={{ fontSize: size, inlineSize: size, blockSize: size }}
    >
      {name}
    </span>
  );
}

/** Requests a typed JSON payload from the local Next.js gateway API. */
async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

/** Formats an ISO timestamp for compact operator-facing rows. */
function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

/** Formats an ISO timestamp as a short clock label. */
function formatClock(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

/** Normalizes event types into readable status chips. */
function eventLabel(type: string): string {
  return type.replace(/[._-]+/g, " ");
}

/** Renders the three-panel local operator workspace backed by TS route handlers. */
export default function GatewayWorkspace() {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [events, setEvents] = useState<GatewayEvent[]>([]);
  const [memory, setMemory] = useState<MemoryRecord[]>([]);
  const [message, setMessage] = useState("Map the hso gateway migration.");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chatTransport = useMemo(() => new DefaultChatTransport({ api: "/api/chat" }), []);
  const {
    sendMessage: sendChatMessage,
    status: chatStatus,
    error: chatError
  } = useChat({
    transport: chatTransport
  });

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [activeSessionId, sessions]
  );
  const isStreaming = chatStatus === "submitted" || chatStatus === "streaming";
  const lastEvent = events.at(-1) ?? null;
  const statusText = error ?? (isStreaming ? "Streaming" : busy ? "Working" : "Ready");
  const statusClassName = error ? "danger" : isStreaming || busy ? "warn" : "ok";
  const userMessages = memory.filter((record) => record.role === "user").length;
  const assistantMessages = memory.filter((record) => record.role === "assistant").length;

  useEffect(() => {
    void refreshSessions();
  }, []);

  useEffect(() => {
    if (chatError) {
      setError(chatError.message);
    }
  }, [chatError]);

  useEffect(() => {
    if (!activeSessionId) {
      setEvents([]);
      setMemory([]);
      return;
    }
    void refreshSessionState(activeSessionId);
  }, [activeSessionId]);

  /** Refreshes the persisted session list from the route handler API. */
  async function refreshSessions() {
    try {
      const nextSessions = await requestJson<SessionRecord[]>("/api/sessions");
      setSessions(nextSessions);
      setActiveSessionId((current) => current ?? nextSessions[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  /** Loads events and memory for the selected session. */
  async function refreshSessionState(sessionId: string) {
    try {
      const [nextEvents, nextMemory] = await Promise.all([
        requestJson<GatewayEvent[]>(`/api/sessions/${sessionId}/events`),
        requestJson<MemoryRecord[]>(`/api/sessions/${sessionId}/memory`)
      ]);
      setEvents(nextEvents);
      setMemory(nextMemory);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  /** Creates a new persisted gateway session and activates it in the UI. */
  async function createSession() {
    setBusy(true);
    setError(null);
    try {
      const session = await requestJson<SessionRecord>("/api/sessions", {
        method: "POST",
        body: JSON.stringify({ title: "Gateway migration" })
      });
      setSessions((current) => [session, ...current]);
      setActiveSessionId(session.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  /** Sends the user task through the AI SDK UI stream and reloads persisted state. */
  async function sendMessage() {
    if (!activeSessionId || !message.trim()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await sendChatMessage(
        { text: message },
        {
          body: { sessionId: activeSessionId }
        }
      );
      await refreshSessionState(activeSessionId);
      setMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="chat-shell">
      <aside className="chat-sidebar" aria-label="Chat history">
        <div className="sidebar-brand">
          <div className="brand-lockup">
            <div className="brand-mark">
              <MaterialIcon name="dns" size={18} />
            </div>
            <div className="brand-copy">
              <span className="brand-eyebrow">hso</span>
              <strong>Research Gateway</strong>
            </div>
          </div>
          <button
            aria-label="Refresh sessions"
            className="ghost-icon-button"
            title="Refresh sessions"
            type="button"
            onClick={refreshSessions}
            disabled={busy}
          >
            <MaterialIcon name="refresh" size={18} />
          </button>
        </div>

        <button className="new-chat-button" type="button" onClick={createSession} disabled={busy}>
          <MaterialIcon name="add" size={17} />
          <span>New chat</span>
        </button>

        <div className="sidebar-section">
          <div className="section-title">
            <MaterialIcon name="history" size={15} />
            <span>History</span>
          </div>
          <div className="session-list">
            {sessions.length === 0 ? (
              <div className="sidebar-empty">
                <MaterialIcon name="auto_awesome" size={17} />
                <span>No sessions yet.</span>
              </div>
            ) : null}
            {sessions.map((session) => (
              <button
                className={`session-row ${session.id === activeSessionId ? "active" : ""}`}
                key={session.id}
                type="button"
                onClick={() => setActiveSessionId(session.id)}
              >
                <span className="session-title">
                  <MaterialIcon name="chat_bubble" size={15} />
                  <span>{session.title}</span>
                </span>
                <span className="session-meta">{formatTimestamp(session.created_at)}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="sidebar-footer">
          <span className={`status-dot ${statusClassName}`} />
          <span>{statusText}</span>
        </div>
      </aside>

      <section className="chat-workspace">
        <header className="chat-topbar">
          <div className="breadcrumb">
            <span>hso</span>
            <MaterialIcon name="chevron_right" size={14} />
            <strong>{activeSession?.title ?? "New chat"}</strong>
          </div>
          <div className="topbar-actions">
            <span className={`status-pill ${statusClassName}`}>
              <span className={`status-dot ${statusClassName}`} />
              {statusText}
            </span>
            <button
              aria-label="Refresh session"
              className="ghost-icon-button"
              title="Refresh session"
              type="button"
              onClick={() => (activeSessionId ? refreshSessionState(activeSessionId) : refreshSessions())}
              disabled={busy}
            >
              <MaterialIcon name="refresh" size={16} />
            </button>
          </div>
        </header>

        <div className="chat-layout">
          <section className="conversation-pane" aria-label="Conversation">
            <div className="chat-thread">
              {memory.length === 0 ? (
                <div className="welcome-panel">
                  <div className="welcome-icon">
                    <MaterialIcon name="smart_toy" size={24} />
                  </div>
                  <div>
                    <h1>What should hso work on?</h1>
                    <p>Start a session, send a research task, and inspect the gateway run as it persists events and memory.</p>
                  </div>
                  <div className="prompt-suggestions" aria-label="Prompt suggestions">
                    <button type="button" onClick={() => setMessage("Map the hso gateway migration.")}>
                      Map the gateway migration
                    </button>
                    <button type="button" onClick={() => setMessage("Summarize the current session memory.")}>
                      Summarize session memory
                    </button>
                    <button type="button" onClick={() => setMessage("List the next implementation risks.")}>
                      List implementation risks
                    </button>
                  </div>
                </div>
              ) : null}

              {memory.map((record) => (
                <article className={`message ${record.role === "user" ? "message-user" : "message-assistant"}`} key={record.id}>
                  <div className="message-avatar">
                    <MaterialIcon name={record.role === "user" ? "keyboard_command_key" : "smart_toy"} size={18} />
                  </div>
                  <div className="message-body">
                    <div className="message-meta">
                      <span>{record.role === "user" ? "You" : "hso-gateway"}</span>
                      <time>{formatClock(record.created_at)}</time>
                    </div>
                    <p>{record.content}</p>
                  </div>
                </article>
              ))}

              {isStreaming ? (
                <article className="message message-assistant">
                  <div className="message-avatar">
                    <MaterialIcon name="smart_toy" size={18} />
                  </div>
                  <div className="message-body">
                    <div className="message-meta">
                      <span>hso-gateway</span>
                      <time>now</time>
                    </div>
                    <p className="typing-line">Thinking through the run...</p>
                  </div>
                </article>
              ) : null}
            </div>

            <div className="composer">
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Send a task to the gateway..."
              />
              <button
                aria-label="Send task"
                className="send-button"
                title="Send task"
                type="button"
                onClick={sendMessage}
                disabled={busy || isStreaming || !activeSessionId || !message.trim()}
              >
                <MaterialIcon name="send" size={17} />
                <span>Send</span>
              </button>
            </div>
          </section>

          <aside className="inspector-pane" aria-label="Run inspector">
            <section className="inspector-card session-card">
              <div className="inspector-header">
                <div>
                  <h2>{activeSession?.title ?? "No session"}</h2>
                  <p>{activeSession ? formatTimestamp(activeSession.created_at) : "Create a chat to begin."}</p>
                </div>
                <span className={`status-pill ${statusClassName}`}>
                  <span className={`status-dot ${statusClassName}`} />
                  {statusText}
                </span>
              </div>
              <div className="stats-grid">
                <div>
                  <strong>{events.length}</strong>
                  <span>events</span>
                </div>
                <div>
                  <strong>{userMessages}</strong>
                  <span>user turns</span>
                </div>
                <div>
                  <strong>{assistantMessages}</strong>
                  <span>agent turns</span>
                </div>
              </div>
            </section>

            <section className="inspector-card">
              <div className="card-title-row">
                <h3>Run activity</h3>
                <span>{lastEvent ? formatClock(lastEvent.created_at) : "idle"}</span>
              </div>
              <div className="activity-list">
                {events.length === 0 ? (
                  <div className="empty-mini">
                    <MaterialIcon name="monitoring" size={17} />
                    <span>No events yet.</span>
                  </div>
                ) : null}
                {events.map((event) => (
                  <article className="activity-row" key={event.id}>
                    <MaterialIcon name="radio_button_checked" size={16} />
                    <div>
                      <div className="activity-meta">
                        <strong>{event.agent_name ?? "gateway"}</strong>
                        <time>{formatClock(event.created_at)}</time>
                      </div>
                      <span>{eventLabel(event.type)}</span>
                      <p>{event.message}</p>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="inspector-card">
              <div className="card-title-row">
                <h3>Memory</h3>
                <span>{memory.length} records</span>
              </div>
              <div className="memory-preview">
                {memory.length === 0 ? (
                  <div className="empty-mini">
                    <MaterialIcon name="memory" size={17} />
                    <span>No memory records.</span>
                  </div>
                ) : null}
                {memory.slice(-4).map((record) => (
                  <article className="memory-item" key={record.id}>
                    <div>
                      <strong>{record.role}</strong>
                      <time>{formatClock(record.created_at)}</time>
                    </div>
                    <p>{record.content}</p>
                  </article>
                ))}
              </div>
            </section>
          </aside>
        </div>
      </section>
    </main>
  );
}
