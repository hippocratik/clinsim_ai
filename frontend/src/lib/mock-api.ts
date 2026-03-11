import mockSession from "@/data/mock_session.json";
import type {
  ApiClient,
  Case,
  SimulationSession,
  SessionStatus,
  ChatMessage,
  OrderedLab,
  DiagnoseRequest,
  DiagnoseResponse,
  CaseScore,
} from "./types";
import { LAB_COSTS } from "./constants";

type MockSessionPayload = typeof mockSession;

let activeSession: MockSessionPayload | null = mockSession;

const LATENCY = {
  fast: 200,
  medium: 600,
  slow: 1200,
};

function delay<T>(value: T, ms: number): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

function toSimulationSession(data: MockSessionPayload): SimulationSession {
  const rawStatus = data.status as string;
  const allowedStatuses: SessionStatus[] = ["active", "completed", "abandoned"];
  const status: SessionStatus = allowedStatuses.includes(
    rawStatus as SessionStatus,
  )
    ? (rawStatus as SessionStatus)
    : "active";

  return {
    session_id: data.session_id,
    case_id: data.case_id,
    trainee_id: data.trainee_id,
    started_at: data.started_at,
    status,
    revealed_info: data.revealed_info,
    ordered_labs: data.ordered_labs,
    actions_taken: data.actions_taken,
    current_score: data.current_score,
  };
}

function toCase(data: MockSessionPayload): Case {
  const raw = data.case;
  return {
    ...raw,
    demographics: {
      ...raw.demographics,
      // Clamp gender to the allowed literal union
      gender: raw.demographics.gender === "M" ? "M" : "F",
    },
    // Normalise null from JSON into undefined for the optional field
    source_case_id: raw.source_case_id ?? undefined,
    available_labs: raw.available_labs.map((lab) => ({
      ...lab,
      // Narrow string to the LabFlag union; treat unknowns as "normal"
      flag:
        lab.flag === "high" ||
        lab.flag === "low" ||
        lab.flag === "critical"
          ? lab.flag
          : "normal",
    })),
    difficulty:
      raw.difficulty === "easy" ||
      raw.difficulty === "medium" ||
      raw.difficulty === "hard"
        ? raw.difficulty
        : "medium",
  };
}

export const mockApi: ApiClient = {
  async getCases(): Promise<Case[]> {
    const data = activeSession ?? mockSession;
    return delay([toCase(data)], LATENCY.fast);
  },

  async createSession(caseId: string): Promise<{ session_id: string }> {
    const base = activeSession ?? mockSession;
    const sessionId = `mock_${caseId}_1`;
    activeSession = {
      ...base,
      session_id: sessionId,
      case_id: caseId,
      status: "active",
      ordered_labs: [],
      actions_taken: [],
      revealed_info: [],
      current_score: 0,
    };
    return delay({ session_id: sessionId }, LATENCY.fast);
  },

  async getSession(sessionId: string): Promise<{
    session: SimulationSession;
    case: Case;
    messages: ChatMessage[];
    orderedLabs: OrderedLab[];
    resourcesUsed: number;
    maxResources: number;
  }> {
    const base = activeSession ?? mockSession;
    // In the purely mock frontend we treat the URL sessionId as authoritative.
    const data: MockSessionPayload = {
      ...base,
      session_id: sessionId,
    };
    activeSession = data;
    const messages: ChatMessage[] = [
      {
        id: "intro-1",
        role: "system",
        content:
          "You are starting an encounter with a simulated patient. Take a focused history, then order targeted tests.",
        createdAt: new Date().toISOString(),
      },
    ];

    return delay(
      {
        session: toSimulationSession(data),
        case: toCase(data),
        messages,
        orderedLabs: [],
        resourcesUsed: 0,
        maxResources: 100,
      },
      LATENCY.fast,
    );
  },

  async sendChat(
    sessionId: string,
    message: string,
  ): Promise<{ response: string }> {
    const data = activeSession ?? mockSession;
    // Keep behavior simple in mock mode: accept any sessionId and respond based on static case.
    const lower = message.toLowerCase();
    let response =
      "I'm not entirely sure how to answer that. Maybe you could ask about my symptoms or medical history?";

    if (lower.includes("brought") || lower.includes("hospital")) {
      response =
        "I've been having this heavy chest pain that started a couple of hours ago and it scared me.";
    } else if (lower.includes("describe") || lower.includes("pain")) {
      response =
        "It feels like a pressure right in the middle of my chest, and it goes into my left arm.";
    } else if (lower.includes("history") || lower.includes("problems")) {
      response =
        "I've had high blood pressure and diabetes for a few years, and my doctor says my cholesterol is high.";
    } else if (lower.includes("medication") || lower.includes("pill")) {
      response =
        "I take metformin for my diabetes, lisinopril for my blood pressure, and a cholesterol pill at night.";
    } else if (lower.includes("allerg")) {
      response = "I don't think I'm allergic to any medications.";
    }

    return delay({ response }, LATENCY.medium);
  },

  async orderLabs(
    sessionId: string,
    labIds: string[],
  ): Promise<{
    orderedLabs: OrderedLab[];
    resourcesUsed: number;
    failedLabs?: Array<{ id: string; reason: string }>;
  }> {
    const data = activeSession ?? mockSession;
    const caseData = toCase(data);
    const orderedLabs: OrderedLab[] = labIds.map((id) => {
      const match = caseData.available_labs.find((lab) =>
        lab.lab_name.toLowerCase().includes(id.toLowerCase()),
      );
      return {
        id,
        name: match?.lab_name ?? id,
        cost: LAB_COSTS[id] ?? 1,
        result: match,
      };
    });

    const resourcesUsed = orderedLabs.length;

    return delay(
      {
        orderedLabs,
        resourcesUsed,
      },
      LATENCY.slow,
    );
  },

  async submitDiagnosis(
    sessionId: string,
    _diagnosis: DiagnoseRequest,
  ): Promise<DiagnoseResponse> {
    const score: CaseScore = {
      session_id: sessionId,
      diagnostic_accuracy: 0.9,
      primary_diagnosis_correct: true,
      differential_score: 0.6,
      efficiency_score: 0.7,
      time_to_diagnosis_seconds: 480,
      labs_ordered: 4,
      optimal_labs: 3,
    };

    const optimalPath = [
      "Clarified onset and character of chest pain",
      "Assessed cardiovascular risk factors",
      "Ordered ECG and cardiac enzymes",
      "Initiated ACS treatment pathway",
    ];

    const traineePath = [
      "Asked about chest pain and associated symptoms",
      "Explored past medical history and medications",
      "Ordered troponin and basic labs",
      "Considered acute coronary syndrome as primary diagnosis",
    ];

    const learningPoints = [
      "Early ECG is critical in suspected myocardial infarction.",
      "Troponin elevation supports the diagnosis but can lag behind symptom onset.",
      "Risk factor assessment helps refine pre-test probability.",
    ];

    return delay(
      {
        score,
        optimalPath,
        traineePath,
        learningPoints,
      },
      LATENCY.medium,
    );
  },

  async getResults(sessionId: string): Promise<DiagnoseResponse> {
    return mockApi.submitDiagnosis(sessionId, {
      primaryDiagnosis: {
        icd9_code: "410.11",
        description: "Acute myocardial infarction",
        is_primary: true,
      },
      differentials: [],
    });
  },

  async searchDiagnoses(query: string): Promise<Diagnosis[]> {
    const q = query.toLowerCase();
    const base: Diagnosis[] = [
      {
        icd9_code: "410.11",
        description:
          "Acute myocardial infarction, STEMI, initial episode",
        is_primary: true,
      },
      {
        icd9_code: "486",
        description: "Pneumonia, organism unspecified",
        is_primary: false,
      },
      {
        icd9_code: "401.9",
        description: "Essential hypertension, unspecified",
        is_primary: false,
      },
      {
        icd9_code: "786.50",
        description: "Chest pain, unspecified",
        is_primary: false,
      },
    ];
    if (!q) return base;
    return base.filter(
      (d) =>
        d.icd9_code.toLowerCase().includes(q) ||
        d.description.toLowerCase().includes(q),
    );
  },
};

