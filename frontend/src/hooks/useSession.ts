import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  Case,
  SimulationSession,
  OrderedLab,
  DiagnoseRequest,
  DiagnoseResponse,
} from "@/lib/types";

interface SessionViewModel {
  session: SimulationSession | null;
  caseData: Case | null;
  orderedLabs: OrderedLab[];
  resourcesUsed: number;
  maxResources: number;
  isLoading: boolean;
  error?: string;
}

export function useSession(sessionId: string) {
  const [state, setState] = useState<SessionViewModel>({
    session: null,
    caseData: null,
    orderedLabs: [],
    resourcesUsed: 0,
    maxResources: 100,
    isLoading: true,
  });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState((prev) => ({ ...prev, isLoading: true, error: undefined }));
      try {
        const data = await api.getSession(sessionId);
        if (cancelled) return;
        setState({
          session: data.session,
          caseData: data.case,
          orderedLabs: data.orderedLabs,
          resourcesUsed: data.resourcesUsed,
          maxResources: data.maxResources,
          isLoading: false,
        });
      } catch (err) {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : "Failed to load session";
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: message,
        }));
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const orderLabs = useCallback(
    async (labIds: string[]) => {
      if (!state.session || labIds.length === 0) return;
      setState((prev) => ({ ...prev, error: undefined }));
      try {
        const res = await api.orderLabs(state.session.session_id, labIds);
        setState((prev) => ({
          ...prev,
          orderedLabs: [...prev.orderedLabs, ...res.orderedLabs],
          resourcesUsed: prev.resourcesUsed + res.resourcesUsed,
        }));
      } catch (err) {
        setState((prev) => ({
          ...prev,
          error: err instanceof Error ? err.message : "Lab order failed",
        }));
      }
    },
    [state.session],
  );

  const submitDiagnosis = useCallback(
    async (payload: DiagnoseRequest): Promise<DiagnoseResponse | null> => {
      if (!state.session) return null;
      setState((prev) => ({ ...prev, error: undefined }));
      try {
        return await api.submitDiagnosis(state.session.session_id, payload);
      } catch (err) {
        setState((prev) => ({
          ...prev,
          error: err instanceof Error ? err.message : "Submit diagnosis failed",
        }));
        return null;
      }
    },
    [state.session],
  );

  return {
    ...state,
    orderLabs,
    submitDiagnosis,
  };
}

