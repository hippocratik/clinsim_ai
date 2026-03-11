import type { ChatMessage } from "@/lib/types";

// Doctor avatar — blue badge with white coat + stethoscope
function DoctorAvatar() {
  return (
    <div className="mt-1 shrink-0">
      <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 rounded-full drop-shadow-sm">
        <circle cx="20" cy="20" r="20" fill="#2563EB"/>
        <circle cx="20" cy="20" r="19" stroke="white" strokeWidth="1.5" fill="none"/>
        <ellipse cx="20" cy="14.5" rx="5.5" ry="5.8" fill="#F5CBA7"/>
        <path d="M14.5 12.5 Q15 7 20 7.5 Q25 7 25.5 12.5 Q23 10.5 20 11 Q17 10.5 14.5 12.5Z" fill="#6B3F1A"/>
        <path d="M10 38 C10 28 14.5 25.5 20 25.5 C25.5 25.5 30 28 30 38" fill="white"/>
        <path d="M20 25.5 L17 32 L14.5 29.5Z" fill="#BFDBFE"/>
        <path d="M20 25.5 L23 32 L25.5 29.5Z" fill="#BFDBFE"/>
        <path d="M16 29.5 Q14 33 16 35.5 Q18 37.5 20 35.5" stroke="#1D4ED8" strokeWidth="1.4" strokeLinecap="round" fill="none"/>
        <circle cx="20" cy="35.5" r="1.4" fill="#1D4ED8"/>
        <path d="M17 25.5 Q20 27 23 25.5" stroke="#E0F2FE" strokeWidth="1" fill="none"/>
      </svg>
    </div>
  );
}

// Patient avatar — light slate circle with hospital gown
function PatientAvatar() {
  return (
    <div className="mt-1 shrink-0">
      <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 rounded-full drop-shadow-sm">
        <circle cx="20" cy="20" r="20" fill="#F1F5F9"/>
        <circle cx="20" cy="20" r="19" stroke="#CBD5E1" strokeWidth="1" fill="none"/>
        <ellipse cx="20" cy="14.5" rx="5.5" ry="5.8" fill="#F5CBA7"/>
        <path d="M14.5 12.5 Q15 7.5 20 7.5 Q25 7.5 25.5 12.5 Q23 10 20 10.5 Q17 10 14.5 12.5Z" fill="#94A3B8"/>
        <path d="M11 38 C11 28 15 25.5 20 25.5 C25 25.5 29 28 29 38" fill="#BAE6FD"/>
        <path d="M17 25.5 Q20 27.5 23 25.5" stroke="#7DD3FC" strokeWidth="1.2" fill="none"/>
        <line x1="20" y1="27" x2="20" y2="35" stroke="#7DD3FC" strokeWidth="1" strokeDasharray="2 2"/>
        <circle cx="16" cy="16" r="1.5" fill="#E8A090" opacity="0.5"/>
        <circle cx="24" cy="16" r="1.5" fill="#E8A090" opacity="0.5"/>
        <path d="M17.5 18 Q20 20 22.5 18" stroke="#C0755A" strokeWidth="1" strokeLinecap="round" fill="none"/>
      </svg>
    </div>
  );
}

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isTrainee = message.role === "trainee";
  const isSystem = message.role === "system";

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <p className="rounded-full bg-slate-100 px-4 py-1.5 text-sm font-medium text-slate-500">
          {message.content}
        </p>
      </div>
    );
  }

  return (
    <div className={`flex w-full gap-3 ${isTrainee ? "flex-row-reverse" : "flex-row"}`}>
      {isTrainee ? <DoctorAvatar /> : <PatientAvatar />}
      <div
        className={`max-w-[78%] rounded-2xl px-4 py-3 text-lg leading-relaxed shadow-sm ${
          isTrainee
            ? "rounded-tr-sm bg-blue-600 text-white"
            : "rounded-tl-sm bg-slate-100 text-slate-800"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}