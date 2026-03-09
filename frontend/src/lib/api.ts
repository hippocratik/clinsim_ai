import { mockApi } from "./mock-api";

const useMock =
  process.env.NEXT_PUBLIC_API_MODE === "mock" ||
  !process.env.NEXT_PUBLIC_API_MODE;

// In the current hackathon build we primarily use the mock API.
// The real API client is wired but minimal; it can be extended to match backend routes.

const realApiBase =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

const realApi = {
  async getCases() {
    const res = await fetch(`${realApiBase}/cases`);
    if (!res.ok) throw new Error("Failed to load cases");
    return res.json();
  },
};

export const api = useMock ? mockApi : realApi;

