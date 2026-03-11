import { LAB_COSTS } from "./constants";
import { mockApi } from "./mock-api";
import type {
  ApiClient,
  Case,
  ChatMessage,
  DiagnoseRequest,
  DiagnoseResponse,
  GetSessionResponse,
  OrderedLab,
  OrderLabsResponse,
  SimulationSession,
} from "./types";
import type { Difficulty } from "./types";

const useMock =
  process.env.NEXT_PUBLIC_API_MODE === "mock" ||
  !process.env.NEXT_PUBLIC_API_MODE;

const realApiBase =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const apiPrefix = `${realApiBase}/api`;

// ─── Backend response shapes (minimal) ─────────────────────────────────────

interface CaseListItem {
  case_id: string;
  difficulty: string;
  specialties: string[];
  presenting_complaint: string;
  is_generated: boolean;
}

interface SessionStateResponse {
  session_id: string;
  case_id: string;
  status: string;
  question_count: number;
  lab_count: number;
  exam_count: number;
  max_questions: number;
  max_labs: number;
  max_exams: number;
  elapsed_seconds: number;
  chat_history: Array<{ role: string; content: string; timestamp: string }>;
  labs_ordered: Array<{ lab_name: string; result: string; ordered_at: string }>;
  exams_performed: unknown[];
}

interface BackendScore {
  primary_diagnosis: number;
  differential: number;
  efficiency: number;
  time_bonus: number;
  total: number;
  feedback: string[];
}

interface ResultsResponse {
  session_id: string;
  score: BackendScore | null;
  elapsed_seconds?: number;
  resources_used?: { questions: number; labs: number; exams: number };
  action_log?: Array<{ action_type: string; detail: string }>;
}

// ─── Helpers ───────────────────────────────────────────────────────────────

const defaultVitals = () => ({
  heart_rate: null as number | null,
  blood_pressure: null as string | null,
  respiratory_rate: null as number | null,
  temperature: null as number | null,
  spo2: null as number | null,
});

function caseListItemToCase(item: CaseListItem): Case {
  const difficulty: Difficulty =
    item.difficulty === "easy" || item.difficulty === "medium" || item.difficulty === "hard"
      ? item.difficulty
      : "medium";
  return {
    case_id: item.case_id,
    subject_id: 0,
    hadm_id: 0,
    demographics: { age: 0, gender: "M", admission_type: "Unknown" },
    presenting_complaint: item.presenting_complaint,
    hpi: "",
    past_medical_history: [],
    medications: [],
    allergies: [],
    physical_exam: { vitals: defaultVitals(), findings: "" },
    available_labs: [],
    diagnoses: [],
    discharge_summary: "",
    difficulty,
    specialties: item.specialties ?? [],
    is_generated: item.is_generated ?? false,
  };
}

function mapBackendScoreToCaseScore(
  sessionId: string,
  score: BackendScore,
  elapsedSeconds: number = 0,
  labsOrdered: number = 0,
  optimalLabs: number = 0
) {
  return {
    session_id: sessionId,
    diagnostic_accuracy: score.total / 100,
    primary_diagnosis_correct: score.primary_diagnosis >= 40,
    differential_score: score.differential / 30,
    efficiency_score: score.efficiency / 30,
    time_to_diagnosis_seconds: elapsedSeconds,
    labs_ordered: labsOrdered,
    optimal_labs: optimalLabs,
  };
}

function mapResultsToDiagnoseResponse(data: ResultsResponse): DiagnoseResponse {
  const sessionId = data.session_id;
  const score = data.score;
  const elapsed = data.elapsed_seconds ?? 0;
  const resources = data.resources_used;
  const labsOrdered = resources?.labs ?? 0;

  if (!score) {
    return {
      score: mapBackendScoreToCaseScore(sessionId, {
        primary_diagnosis: 0,
        differential: 0,
        efficiency: 0,
        time_bonus: 0,
        total: 0,
        feedback: [],
      }, elapsed, labsOrdered, 0),
      optimalPath: [],
      traineePath: (data.action_log ?? []).map((a) => a.detail || a.action_type),
      learningPoints: [],
    };
  }

  return {
    score: mapBackendScoreToCaseScore(sessionId, score, elapsed, labsOrdered, 0),
    optimalPath: [],
    traineePath: (data.action_log ?? []).map((a) => a.detail || a.action_type),
    learningPoints: Array.isArray(score.feedback) ? score.feedback : [],
  };
}

// ─── Real API ──────────────────────────────────────────────────────────────

const realApi: ApiClient = {
  async getCases(): Promise<Case[]> {
    const res = await fetch(`${apiPrefix}/cases`);
    if (!res.ok) throw new Error("Failed to load cases");
    const list: CaseListItem[] = await res.json();
    return list.map(caseListItemToCase);
  },

  async createSession(caseId: string): Promise<{ session_id: string }> {
    const res = await fetch(`${apiPrefix}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ case_id: caseId }),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Failed to create session");
    }
    const data = await res.json();
    return { session_id: data.session_id };
  },

  async getSession(sessionId: string): Promise<GetSessionResponse> {
    const res = await fetch(`${apiPrefix}/sessions/${encodeURIComponent(sessionId)}`);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Session not found");
    }
    const state: SessionStateResponse = await res.json();

    let caseItem: CaseListItem;
    try {
      const caseRes = await fetch(`${apiPrefix}/cases/${encodeURIComponent(state.case_id)}`);
      if (!caseRes.ok) throw new Error("Case not found");
      caseItem = await caseRes.json();
    } catch {
      caseItem = {
        case_id: state.case_id,
        difficulty: "medium",
        specialties: [],
        presenting_complaint: "",
        is_generated: false,
      };
    }

    const session: SimulationSession = {
      session_id: state.session_id,
      case_id: state.case_id,
      trainee_id: "trainee",
      started_at: state.chat_history?.[0]?.timestamp ?? new Date().toISOString(),
      status: state.status === "completed" ? "completed" : state.status === "abandoned" ? "abandoned" : "active",
      revealed_info: [],
      ordered_labs: state.labs_ordered.map((l) => l.lab_name),
      actions_taken: [],
      current_score: 0,
    };

    const messages: ChatMessage[] = state.chat_history.map((m, i) => ({
      id: `msg-${i}-${m.timestamp}`,
      role: m.role === "trainee" ? "trainee" : m.role === "patient" ? "patient" : "system",
      content: m.content,
      createdAt: m.timestamp,
    }));

    const orderedLabs = state.labs_ordered.map((l) => ({
      id: l.lab_name,
      name: l.lab_name,
      cost: LAB_COSTS[l.lab_name] ?? 1,
      result: {
        lab_name: l.lab_name,
        value: l.result,
        unit: "",
        flag: "normal" as const,
      },
    }));

    const resourcesUsed = orderedLabs.reduce((sum, lab) => sum + lab.cost, 0);

    return {
      session,
      case: caseListItemToCase(caseItem),
      messages,
      orderedLabs,
      resourcesUsed,
      maxResources: state.max_labs ?? 100,
    };
  },

  async sendChat(
    sessionId: string,
    message: string
  ): Promise<{ response: string }> {
    const res = await fetch(`${apiPrefix}/sessions/${encodeURIComponent(sessionId)}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Chat request failed");
    }
    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let fullResponse = "";
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const json = JSON.parse(line.slice(6)) as { token?: string; done?: boolean; full_response?: string };
            if (json.token) fullResponse += json.token;
            if (json.done && json.full_response !== undefined) fullResponse = json.full_response;
          } catch {
            // skip malformed lines
          }
        }
      }
    }
    if (buffer.startsWith("data: ")) {
      try {
        const json = JSON.parse(buffer.slice(6)) as { full_response?: string };
        if (json.full_response !== undefined) fullResponse = json.full_response;
      } catch {
        // ignore
      }
    }
    return { response: fullResponse };
  },

  async orderLabs(
    sessionId: string,
    labIds: string[]
  ): Promise<OrderLabsResponse> {
    const orderedLabs: OrderedLab[] = [];
    for (const id of labIds) {
      const labName = id;
      const res = await fetch(`${apiPrefix}/sessions/${encodeURIComponent(sessionId)}/labs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lab_name: labName }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Lab order failed");
      }
      const data = (await res.json()) as { lab_name: string; result: string };
      orderedLabs.push({
        id: data.lab_name,
        name: data.lab_name,
        cost: LAB_COSTS[data.lab_name] ?? 1,
        result: {
          lab_name: data.lab_name,
          value: data.result,
          unit: "",
          flag: "normal",
        },
      });
    }
    const resourcesUsed = orderedLabs.reduce((sum, lab) => sum + lab.cost, 0);
    return { orderedLabs, resourcesUsed };
  },

  async submitDiagnosis(
    sessionId: string,
    diagnosis: DiagnoseRequest
  ): Promise<DiagnoseResponse> {
    const res = await fetch(`${apiPrefix}/sessions/${encodeURIComponent(sessionId)}/diagnose`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        primary_diagnosis: diagnosis.primaryDiagnosis.icd9_code,
        differentials: diagnosis.differentials.map((d) => d.icd9_code),
      }),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Submit diagnosis failed");
    }
    const data = await res.json() as { session_id: string; status: string; score: BackendScore | null };
    if (!data.score) {
      return {
        score: mapBackendScoreToCaseScore(data.session_id, {
          primary_diagnosis: 0,
          differential: 0,
          efficiency: 0,
          time_bonus: 0,
          total: 0,
          feedback: [],
        }),
        optimalPath: [],
        traineePath: [],
        learningPoints: [],
      };
    }
    return {
      score: mapBackendScoreToCaseScore(data.session_id, data.score),
      optimalPath: [],
      traineePath: [],
      learningPoints: Array.isArray(data.score.feedback) ? data.score.feedback : [],
    };
  },

  async getResults(sessionId: string): Promise<DiagnoseResponse> {
    const res = await fetch(`${apiPrefix}/sessions/${encodeURIComponent(sessionId)}/results`);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Failed to load results");
    }
    const data: ResultsResponse = await res.json();
    return mapResultsToDiagnoseResponse(data);
  },
};

export const api: ApiClient = useMock ? mockApi : realApi;
