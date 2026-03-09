import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/types";
import { api } from "@/lib/api";

interface UsePatientChatOptions {
  sessionId: string;
  initialMessages?: ChatMessage[];
}

const STREAM_DELAY_MS = 18;

export function usePatientChat(options: UsePatientChatOptions) {
  const { sessionId, initialMessages = [] } = options;
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [isSending, setIsSending] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(
    null,
  );

  const streamTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (streamTimeoutRef.current !== null) {
        window.clearTimeout(streamTimeoutRef.current);
      }
    };
  }, []);

  const appendMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const streamPatientResponse = useCallback((fullText: string) => {
    const id = `patient-${Date.now()}`;
    const createdAt = new Date().toISOString();
    setStreamingMessageId(id);

    appendMessage({
      id,
      role: "patient",
      content: "",
      createdAt,
    });

    let index = 0;

    const step = () => {
      index += 1;
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === id ? { ...msg, content: fullText.slice(0, index) } : msg,
        ),
      );

      if (index < fullText.length) {
        streamTimeoutRef.current = window.setTimeout(step, STREAM_DELAY_MS);
      } else {
        setStreamingMessageId(null);
        streamTimeoutRef.current = null;
      }
    };

    step();
  }, [appendMessage]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isSending) return;
      setIsSending(true);

      const traineeMessage: ChatMessage = {
        id: `trainee-${Date.now()}`,
        role: "trainee",
        content,
        createdAt: new Date().toISOString(),
      };

      appendMessage(traineeMessage);

      try {
        const result = await api.sendChat(sessionId, content);
        streamPatientResponse(result.response);
      } finally {
        setIsSending(false);
      }
    },
    [appendMessage, sessionId, isSending, streamPatientResponse],
  );

  return {
    messages,
    isSending,
    streamingMessageId,
    sendMessage,
  };
}

