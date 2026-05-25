"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { Bot, Brain, CircleDot, Plus, Send, Server } from "lucide-react";
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

  const isStreaming = chatStatus === "submitted" || chatStatus === "streaming";

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="panel-header">
          <div className="brand">
            <Server size={18} />
            <span>hso</span>
          </div>
          <button className="icon-button" type="button" onClick={createSession} disabled={busy}>
            <Plus size={17} />
          </button>
        </div>
        <div className="session-list">
          {sessions.length === 0 ? <div className="empty">No sessions yet.</div> : null}
          {sessions.map((session) => (
            <button
              className={`session-row ${session.id === activeSessionId ? "active" : ""}`}
              key={session.id}
              type="button"
              onClick={() => setActiveSessionId(session.id)}
            >
              <div>{session.title}</div>
              <div className="muted">{new Date(session.created_at).toLocaleString()}</div>
            </button>
          ))}
        </div>
      </aside>

      <section className="main">
        <div className="panel-header">
          <div className="main-title">
            <Bot size={19} />
            <h1>{activeSession?.title ?? "Gateway workspace"}</h1>
          </div>
          <span className="muted">{error ?? "TypeScript gateway / AI SDK stream"}</span>
        </div>
        <div className="timeline">
          {events.length === 0 ? <div className="empty">Create a session and send a task.</div> : null}
          {events.map((event) => (
            <article className="event-row" key={event.id}>
              <CircleDot size={18} />
              <div>
                <div className="eyebrow">{event.agent_name ?? "gateway"} · {event.type}</div>
                <p className="event-copy">{event.message}</p>
              </div>
            </article>
          ))}
        </div>
        <div className="composer">
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Send a task to the gateway..."
          />
          <button
            className="send-button"
            type="button"
            onClick={sendMessage}
            disabled={busy || isStreaming || !activeSessionId || !message.trim()}
          >
            <Send size={17} />
          </button>
        </div>
      </section>

      <aside className="memory">
        <div className="panel-header">
          <div className="brand">
            <Brain size={18} />
            <span>Memory</span>
          </div>
        </div>
        <div className="memory-list">
          {memory.length === 0 ? <div className="empty">No memory records.</div> : null}
          {memory.map((record) => (
            <article className="memory-row" key={record.id}>
              <div className="eyebrow">{record.role}</div>
              <p className="memory-copy">{record.content}</p>
            </article>
          ))}
        </div>
      </aside>
    </main>
  );
}
