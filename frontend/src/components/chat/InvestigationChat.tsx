import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { sendEngineeringChat } from "../../lib/api/chat";

type Message = { role: "user" | "assistant"; text: string };

export function InvestigationChat({ investigationId, sessionId }: { investigationId: number; sessionId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const disabled = !investigationId || investigationId <= 0 || loading;

  const storageKey = `investigation_chat_${sessionId}_${investigationId}`;

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
  }, [messages, storageKey, sessionId]);

  async function handleSend(e?: FormEvent) {
    e?.preventDefault();
    if (!input.trim() || disabled) return;

    const userText = input.trim();
    setInput("");
    const userEntry: Message = { role: "user", text: userText };
    setMessages((prev) => [...prev, userEntry]);
    setLoading(true);

    try {
      const res = await sendEngineeringChat(investigationId, { question: userText });
      const answer = res?.answer ?? "(no answer)";
      setMessages((prev) => [...prev, { role: "assistant", text: answer }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "Chat request failed. Check backend logs." }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-[hsl(var(--secondary))]">
              <svg className="h-5 w-5 text-[hsl(var(--muted-foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
              </svg>
            </div>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              {disabled ? "Load an investigation to start chatting" : "Ask a question about your investigation"}
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
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-[hsl(var(--border))] p-4">
        <form onSubmit={handleSend} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={disabled ? "Load an investigation first..." : "Ask a question..."}
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
      </div>
    </div>
  );
}
