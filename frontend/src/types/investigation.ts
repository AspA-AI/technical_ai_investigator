export interface InvestigationState {
  anomalies: unknown[];
  incidents: unknown[];
  root_causes: unknown[];
  recommendations: unknown[];
  summary: string;
}

export interface InvestigationRun {
  investigation_id: number;
  upload_id: string;
  status: string;
  state: InvestigationState;
}
