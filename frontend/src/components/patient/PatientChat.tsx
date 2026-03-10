"use client";

import { useEffect, useRef, useState } from "react";
import { usePatientChat } from "@/hooks/usePatientChat";
import type { ChatMessage } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";

const SUGGESTED_QUESTIONS = [
  "What brought you to the hospital today?",
  "When did your symptoms start?",
  "Have you experienced this before?",
  "Do you have any allergies?",
  "What medications are you taking?",
];

interface PatientChatProps {
  sessionId: string;
  initialMessages?: ChatMessage[];
}

export function PatientChat({ sessionId, initialMessages }: PatientChatProps) {
  const [input, setInput] = useState("");
  const { messages, isSending, streamingMessageId, sendMessage } = usePatientChat({
    sessionId,
    initialMessages,
  });
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const value = input;
    setInput("");
    await sendMessage(value);
  };

  const handleSuggested = async (q: string) => {
    setInput("");
    await sendMessage(q);
  };

  return (
    <div className="flex max-h-[70vh] flex-col rounded-3xl border border-slate-200 bg-white/60 shadow-sm backdrop-blur">
      <div className="border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-semibold tracking-tight text-slate-900">
          Patient Conversation
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Take a focused history. Your questions shape what you learn.
        </p>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 space-y-3 overflow-y-auto px-4 py-4"
      >
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {streamingMessageId && (
          <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
            <span>Patient is responding…</span>
          </div>
        )}
      </div>

      <div className="border-t border-slate-100 bg-slate-50/60 px-4 py-3">
        <div className="mb-2 flex flex-wrap gap-1.5">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              className="rounded-full bg-white px-3 py-1 text-[11px] font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 hover:bg-slate-100"
              onClick={() => handleSuggested(q)}
              disabled={isSending}
            >
              {q}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSend();
              }
            }}
            placeholder="Type your next question to the patient…"
            className="flex-1 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-blue-200 focus:border-blue-500 focus:ring-2"
          />
          <button
            type="button"
            onClick={() => void handleSend()}
            disabled={isSending || !input.trim()}
            className="inline-flex items-center justify-center rounded-2xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
          >
            {isSending ? "Sending…" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

