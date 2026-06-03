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
    <div>
      <form onSubmit={handleSend} className="space-y-3">
        <div className="max-h-72 overflow-auto space-y-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
          {messages.length === 0 ? (
            <div className="text-sm text-slate-500">No messages yet. Ask a question about the loaded investigation.</div>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${m.role === "user" ? "bg-cyan-600 text-white" : "bg-slate-800 text-slate-200"}`}>
                  {m.text}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="flex gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={disabled ? "Load an investigation to enable chat" : "Ask a question..."}
            disabled={disabled}
            className="flex-1 rounded-2xl border border-slate-800 bg-slate-950/90 px-4 py-3 text-sm text-slate-100 outline-none"
          />
          <button type="submit" disabled={disabled} className="rounded-2xl bg-slate-700 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">
            {loading ? "Sending..." : "Send"}
          </button>
        </div>
      </form>
    </div>
  );
}
