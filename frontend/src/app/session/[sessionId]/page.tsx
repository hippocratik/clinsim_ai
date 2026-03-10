import { notFound, redirect } from "next/navigation";
import { api } from "@/lib/api";
import { SessionClient } from "./SessionClient";

interface SessionPageParams {
  sessionId: string;
}

async function ensureSession(sessionId: string) {
  // For the mock API, if the session id is actually a case id, create a session first.
  if (sessionId.startsWith("case_")) {
    const created = await api.createSession(sessionId);
    redirect(`/session/${encodeURIComponent(created.session_id)}`);
  }
}

export default async function SessionPage(props: {
  params: Promise<SessionPageParams>;
}) {
  const { sessionId } = await props.params;

  // Try to ensure there is a usable session on the server; 404 if not.
  await ensureSession(sessionId);
  const result = await api.getSession(sessionId).catch(() => null);
  if (!result) {
    notFound();
  }

  // This component is a server stub that hands off to a client component for hooks/state.
  return <SessionClient sessionId={sessionId} />;
}

