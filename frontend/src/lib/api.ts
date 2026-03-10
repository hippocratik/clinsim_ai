import { mockApi } from "./mock-api";
import type {
  ApiClient,
  Case,
  DiagnoseRequest,
  DiagnoseResponse,
  GetSessionResponse,
  OrderLabsResponse,
} from "./types";

const useMock =
  process.env.NEXT_PUBLIC_API_MODE === "mock" ||
  !process.env.NEXT_PUBLIC_API_MODE;

// In the current hackathon build we primarily use the mock API.
// The real API client is wired but minimal; it can be extended to match backend routes.

const realApiBase =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

const notImplemented = (method: string): never => {
  throw new Error(
    `Not implemented: ${method}. Wire this to the FastAPI backend (see backend API spec).`,
  );
};

const realApi: ApiClient = {
  async getCases(): Promise<Case[]> {
    const res = await fetch(`${realApiBase}/cases`);
    if (!res.ok) throw new Error("Failed to load cases");
    return res.json();
  },
  async createSession(_caseId: string): Promise<{ session_id: string }> {
    return notImplemented("api.createSession");
  },
  async getSession(_sessionId: string): Promise<GetSessionResponse> {
    return notImplemented("api.getSession");
  },
  async sendChat(
    _sessionId: string,
    _message: string,
  ): Promise<{ response: string }> {
    return notImplemented("api.sendChat");
  },
  async orderLabs(
    _sessionId: string,
    _labIds: string[],
  ): Promise<OrderLabsResponse> {
    return notImplemented("api.orderLabs");
  },
  async submitDiagnosis(
    _sessionId: string,
    _diagnosis: DiagnoseRequest,
  ): Promise<DiagnoseResponse> {
    return notImplemented("api.submitDiagnosis");
  },
};

export const api: ApiClient = useMock ? mockApi : realApi;

