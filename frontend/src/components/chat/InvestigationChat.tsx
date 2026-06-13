import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { io, type Socket } from "socket.io-client";

type ChatSocketAck = {
  ok: boolean;
  answer?: string;
  error?: string;
  code?: string;
};

type Message = { role: "user" | "assistant"; text: string };
type Conversation = {
  investigationId: number;
  updatedAt: number;
  preview: string;
  messageCount: number;
};

export function InvestigationChat({
  investigationId,
  sessionId,
  onSelectInvestigationId,
  historyOpen,
  onCloseHistory,
}: {
  investigationId: number;
  sessionId: string;
  onSelectInvestigationId?: (id: number) => void;
  historyOpen?: boolean;
  onCloseHistory?: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [socketConnected, setSocketConnected] = useState(false);
  const [socketError, setSocketError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const disabled = !investigationId || investigationId <= 0 || loading || !socketConnected;
  const socketRef = useRef<Socket | null>(null);

  const storageKey = `investigation_chat_${sessionId}_${investigationId}`;
  const indexKey = `investigation_chat_index_${sessionId}`;
  const endRef = useRef<HTMLDivElement | null>(null);

  const storagePrefix = useMemo(() => `investigation_chat_${sessionId}_`, [sessionId]);
  const socketBaseUrl =
    import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ||
    (typeof window !== "undefined" ? window.location.origin : "");

  const rebuildConversationIndex = () => {
    if (typeof window === "undefined") return;
    if (!sessionId) return;

    const next: Conversation[] = [];
    for (let i = 0; i < window.localStorage.length; i += 1) {
      const key = window.localStorage.key(i);
      if (!key) continue;
      if (!key.startsWith(storagePrefix)) continue;

      const idPart = key.slice(storagePrefix.length);
      const id = Number(idPart);
      if (!Number.isFinite(id) || id <= 0) continue;

      const raw = window.localStorage.getItem(key);
      if (!raw) continue;
      try {
        const parsed = JSON.parse(raw) as Message[];
        if (!Array.isArray(parsed) || parsed.length === 0) continue;
        const last = parsed[parsed.length - 1];
        next.push({
          investigationId: id,
          updatedAt: Date.now(),
          preview: typeof last?.text === "string" ? last.text : "",
          messageCount: parsed.length,
        });
      } catch {
        continue;
      }
    }

    next.sort((a, b) => b.updatedAt - a.updatedAt);
    window.localStorage.setItem(indexKey, JSON.stringify(next));
    setConversations(next);
  };

  const loadConversationIndex = () => {
    if (typeof window === "undefined") return;
    if (!sessionId) return;

    const raw = window.localStorage.getItem(indexKey);
    if (!raw) {
      rebuildConversationIndex();
      return;
    }

    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        rebuildConversationIndex();
        return;
      }
      const normalized = parsed
        .map((item) => ({
          investigationId: Number(item?.investigationId),
          updatedAt: Number(item?.updatedAt),
          preview: typeof item?.preview === "string" ? item.preview : "",
          messageCount: Number(item?.messageCount),
        }))
        .filter(
          (item) =>
            Number.isFinite(item.investigationId) &&
            item.investigationId > 0 &&
            Number.isFinite(item.updatedAt) &&
            item.updatedAt > 0 &&
            Number.isFinite(item.messageCount)
        )
        .sort((a, b) => b.updatedAt - a.updatedAt);
      setConversations(normalized);
    } catch {
      rebuildConversationIndex();
    }
  };

  const updateConversationIndex = (nextMessages: Message[]) => {
    if (typeof window === "undefined") return;
    if (!sessionId) return;
    if (!investigationId || investigationId <= 0) return;
    if (nextMessages.length === 0) return;

    const last = nextMessages[nextMessages.length - 1];
    const entry: Conversation = {
      investigationId,
      updatedAt: Date.now(),
      preview: typeof last?.text === "string" ? last.text : "",
      messageCount: nextMessages.length,
    };

    setConversations((prev) => {
      const merged = [entry, ...prev.filter((c) => c.investigationId !== investigationId)].slice(0, 25);
      window.localStorage.setItem(indexKey, JSON.stringify(merged));
      return merged;
    });
  };

  useEffect(() => {
    if (!sessionId || !investigationId) {
      setSocketConnected(false);
      setSocketError(null);
      socketRef.current?.disconnect();
      socketRef.current = null;
      return;
    }

    const socket = io(socketBaseUrl, {
      path: "/socket.io",
      transports: ["websocket", "polling"],
      withCredentials: true,
      auth: {
        sessionId,
        investigationId,
      },
    });

    socketRef.current = socket;
    setSocketConnected(false);
    setSocketError(null);

    const handleConnect = () => {
      setSocketConnected(true);
      setSocketError(null);
    };
    const handleDisconnect = () => setSocketConnected(false);
    const handleConnectError = (error: unknown) => {
      setSocketConnected(false);
      setSocketError(error instanceof Error ? error.message : "Unable to connect to chat socket.");
    };

    socket.on("connect", handleConnect);
    socket.on("disconnect", handleDisconnect);
    socket.on("connect_error", handleConnectError);

    return () => {
      socket.off("connect", handleConnect);
      socket.off("disconnect", handleDisconnect);
      socket.off("connect_error", handleConnectError);
      socket.disconnect();
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
    };
  }, [investigationId, sessionId, socketBaseUrl]);

  useEffect(() => {
    loadConversationIndex();
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    const saved = typeof window !== "undefined" ? window.localStorage.getItem(storageKey) : null;
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Message[];
        setMessages(parsed);
      } catch {
        setMessages([]);
      }
    } else {
      setMessages([]);
    }
  }, [storageKey, sessionId, investigationId]);

  useEffect(() => {
    if (!sessionId) return;
    if (messages.length === 0) return;
    if (typeof window === "undefined") return;
    window.localStorage.setItem(storageKey, JSON.stringify(messages));
    updateConversationIndex(messages);
  }, [messages, storageKey, sessionId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading, investigationId]);

  const closeHistory = () => {
    onCloseHistory?.();
  };

  const selectConversation = (id: number) => {
    onSelectInvestigationId?.(id);
    closeHistory();
  };

  async function handleSend(e?: FormEvent) {
    e?.preventDefault();
    if (!input.trim() || disabled) return;

    const userText = input.trim();
    setInput("");
    const userEntry: Message = { role: "user", text: userText };
    const history = messages.map((message) => ({
      role: message.role,
      content: message.text,
    }));
    setMessages((prev) => [...prev, userEntry]);
    setLoading(true);

    try {
      const socket = socketRef.current;
      if (!socket || !socket.connected) {
        throw new Error("Socket connection is not ready yet.");
      }

      const answer = await new Promise<string>((resolve, reject) => {
        const timeout = window.setTimeout(() => {
          reject(new Error("Chat request timed out."));
        }, 30000);

        socket.emit(
          "chat:message",
          {
            investigation_id: investigationId,
            question: userText,
            history,
            session_id: sessionId,
          },
          (response: ChatSocketAck) => {
            window.clearTimeout(timeout);
            if (!response?.ok) {
              reject(new Error(response?.error || "Chat request failed."));
              return;
            }
            resolve(response.answer ?? "(no answer)");
          }
        );
      });

      setMessages((prev) => [...prev, { role: "assistant", text: answer }]);
    } catch (error) {
      const fallback = error instanceof Error ? error.message : "Chat request failed. Check backend logs.";
      setMessages((prev) => [...prev, { role: "assistant", text: fallback }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex h-full flex-col">
      <div className={`absolute inset-0 z-20 ${historyOpen ? "" : "pointer-events-none"}`}>
        <div
          className={`absolute inset-0 bg-black/40 transition-opacity ${historyOpen ? "opacity-100" : "opacity-0"}`}
          onClick={closeHistory}
        />
        <div
          className={`absolute right-0 top-0 flex h-full w-[280px] flex-col border-l border-[hsl(var(--border))] bg-[hsl(var(--card))] shadow-2xl transition-transform ${
            historyOpen ? "translate-x-0" : "translate-x-full"
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-4 py-3">
            <div className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
              Chat History
            </div>
            <button
              type="button"
              onClick={closeHistory}
              className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--secondary))]"
              title="Close"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            {conversations.length === 0 ? (
              <div className="px-1 text-xs text-[hsl(var(--muted-foreground))]">No chats yet</div>
            ) : (
              <div className="space-y-2">
                {conversations.map((c) => (
                  <button
                    key={c.investigationId}
                    type="button"
                    onClick={() => selectConversation(c.investigationId)}
                    className={`w-full rounded-lg px-3 py-2 text-left text-xs transition-colors ${
                      c.investigationId === investigationId
                        ? "bg-[hsl(var(--secondary))] text-[hsl(var(--foreground))]"
                        : "border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--secondary))]"
                    }`}
                    title={c.preview}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">#{c.investigationId}</span>
                      <span className="text-[10px]">{c.messageCount}</span>
                    </div>
                    <div className="mt-1 truncate text-[11px]">{c.preview || " "}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-[hsl(var(--secondary))]">
              <svg className="h-5 w-5 text-[hsl(var(--muted-foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
              </svg>
            </div>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              {!investigationId || investigationId <= 0
                ? "Load an investigation to start chatting"
                : socketConnected
                  ? "Ask a question about your investigation"
                  : "Connecting chat socket..."}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm ${
                    m.role === "user"
                      ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                      : "border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--foreground))]"
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3.5 py-2.5">
                  <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-[hsl(var(--muted-foreground))]" style={{ animationDelay: "0ms" }} />
                  <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-[hsl(var(--muted-foreground))]" style={{ animationDelay: "150ms" }} />
                  <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-[hsl(var(--muted-foreground))]" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <div className="border-t border-[hsl(var(--border))] p-4">
        <form onSubmit={handleSend} className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              !investigationId || investigationId <= 0
                ? "Load an investigation first..."
                : socketConnected
                  ? "Ask a question..."
                  : "Connecting chat socket..."
            }
            disabled={disabled}
            className="flex-1 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3.5 py-2.5 text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))] disabled:cursor-not-allowed disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={disabled}
            className="inline-flex items-center justify-center rounded-lg bg-[hsl(var(--primary))] px-4 py-2.5 text-sm font-medium text-[hsl(var(--primary-foreground))] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </form>
        {socketError && (
          <p className="mt-2 text-xs text-[hsl(var(--destructive))]">{socketError}</p>
        )}
      </div>
    </div>
  );
}
