export type Difficulty = "easy" | "medium" | "hard";

export interface Demographics {
  age: number;
  gender: "M" | "F";
  admission_type: string;
}

export interface Vitals {
  heart_rate: number | null;
  blood_pressure: string | null;
  respiratory_rate: number | null;
  temperature: number | null;
  spo2: number | null;
}

export interface PhysicalExam {
  vitals: Vitals;
  findings: string;
}

export type LabFlag = "normal" | "high" | "low" | "critical";

export interface LabResult {
  lab_name: string;
  value: string;
  unit: string;
  flag: LabFlag;
}

export interface Diagnosis {
  icd9_code: string;
  description: string;
  is_primary: boolean;
}

export interface Case {
  case_id: string;
  subject_id: number;
  hadm_id: number;
  demographics: Demographics;
  presenting_complaint: string;
  hpi: string;
  past_medical_history: string[];
  medications: string[];
  allergies: string[];
  physical_exam: PhysicalExam;
  available_labs: LabResult[];
  diagnoses: Diagnosis[];
  discharge_summary: string;
  difficulty: Difficulty;
  specialties: string[];
  source_case_id?: string;
  is_generated: boolean;
}

export interface CaseChunk {
  chunk_id: string;
  case_id: string;
  chunk_type:
    | "presenting_complaint"
    | "hpi"
    | "pmh"
    | "physical_exam"
    | "labs"
    | "medications"
    | "hospital_course"
    | "diagnosis";
  content: string;
  metadata: {
    subject_id: number;
    hadm_id: number;
    icd9_codes: string[];
  };
  embedding?: number[];
}

export type SessionStatus = "active" | "completed" | "abandoned";

export interface TraineeAction {
  action_type: "ask_question" | "order_lab" | "perform_exam" | "submit_diagnosis";
  content: string;
  timestamp: string;
  cost: number;
}

/**
 * TODO: Validate against backend Session model when Issue #3 ships.
 * Assumed shape — backend must match or this type must be updated.
 * Key risk: `current_score` may become a full CaseScore object, not a number.
 */
export interface SimulationSession {
  session_id: string;
  case_id: string;
  trainee_id: string;
  started_at: string;
  status: SessionStatus;
  revealed_info: string[];
  ordered_labs: string[];
  actions_taken: TraineeAction[];
  current_score: number;
}

export type ChatRole = "trainee" | "patient" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
}

export interface OrderedLab {
  id: string;
  name: string;
  cost: number;
  result?: LabResult;
}

export interface PatientResponse {
  response: string;
  revealed_chunks: string[];
  confidence: number;
}

export interface CaseScore {
  session_id: string;
  diagnostic_accuracy: number;
  primary_diagnosis_correct: boolean;
  differential_score: number;
  efficiency_score: number;
  time_to_diagnosis_seconds: number;
  labs_ordered: number;
  optimal_labs: number;
}

export interface DiagnoseRequest {
  primaryDiagnosis: Diagnosis;
  differentials: Diagnosis[];
  reasoning?: string;
}

export interface DiagnoseResponse {
  score: CaseScore;
  optimalPath: string[];
  traineePath: string[];
  learningPoints: string[];
}

export interface GetSessionResponse {
  session: SimulationSession;
  case: Case;
  messages: ChatMessage[];
  orderedLabs: OrderedLab[];
  resourcesUsed: number;
  maxResources: number;
}

export interface OrderLabsResponse {
  orderedLabs: OrderedLab[];
  resourcesUsed: number;
  failedLabs?: Array<{
    id: string;
    reason: string;
  }>;
}

export interface ApiClient {
  getCases(): Promise<Case[]>;
  createSession(caseId: string): Promise<{ session_id: string }>;
  getSession(sessionId: string): Promise<GetSessionResponse>;
  sendChat(
    sessionId: string,
    message: string,
  ): Promise<{ response: string }>;
  orderLabs(sessionId: string, labIds: string[]): Promise<OrderLabsResponse>;
  submitDiagnosis(
    sessionId: string,
    diagnosis: DiagnoseRequest,
  ): Promise<DiagnoseResponse>;
  getResults(sessionId: string): Promise<DiagnoseResponse>;
}


