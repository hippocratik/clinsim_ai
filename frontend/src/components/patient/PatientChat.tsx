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
    // h-full fills whatever height SessionClient gives us
    <div className="flex h-full flex-col">

      {/* Header — fixed */}
      <div className="shrink-0 border-b border-slate-100 px-6 py-3">
        <h2 className="text-xl font-bold text-slate-900">Patient Conversation</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          Take a focused history. Your questions shape what you learn.
        </p>
      </div>

      {/* Messages — scrollable, fills remaining space */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 px-6 py-5">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-3xl">🩺</div>
            <div>
              <p className="text-base font-semibold text-slate-700">Begin your consultation</p>
              <p className="mt-1 text-sm text-slate-400">Ask the patient a question or pick one below.</p>
            </div>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {streamingMessageId && (
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-400 [animation-delay:0ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-400 [animation-delay:150ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-400 [animation-delay:300ms]" />
            </div>
            <span className="text-sm text-slate-400">Patient is responding…</span>
          </div>
        )}
      </div>

      {/* Input — pinned to bottom */}
      <div className="shrink-0 border-t border-slate-100 bg-slate-50/60 px-6 py-3">
        <div className="mb-3 flex flex-wrap gap-2">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => handleSuggested(q)}
              disabled={isSending}
              className="rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-sm font-medium text-slate-600 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 disabled:opacity-40"
            >
              {q}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void handleSend(); }
            }}
            placeholder="Type your next question to the patient…"
            className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-base outline-none placeholder:text-slate-400 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100"
          />
          <button
            type="button"
            onClick={() => void handleSend()}
            disabled={isSending || !input.trim()}
            className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-base font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isSending
              ? <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" /><span>Sending</span></>
              : "Send ↵"
            }
          </button>
        </div>
      </div>
    </div>
  );
}