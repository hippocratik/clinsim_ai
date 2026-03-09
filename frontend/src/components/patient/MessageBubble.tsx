import type { ChatMessage } from "@/lib/types";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isTrainee = message.role === "trainee";
  const isPatient = message.role === "patient";

  const alignment = isTrainee ? "items-end" : "items-start";
  const bubbleColor = isTrainee
    ? "bg-blue-600 text-white"
    : isPatient
      ? "bg-emerald-50 text-emerald-900 border border-emerald-100"
      : "bg-slate-100 text-slate-700 border border-slate-200";

  return (
    <div className={`flex w-full ${alignment}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm leading-relaxed shadow-sm ${bubbleColor}`}
      >
        {message.content}
      </div>
    </div>
  );
}

