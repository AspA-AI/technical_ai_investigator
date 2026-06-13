export interface InvestigationState {
  risk_level?: string;
  anomalies: unknown[];
  incidents: unknown[];
  github_matches?: unknown[];
  github_match_status?: string;
  root_causes: unknown[];
  recommendations: unknown[];
  summary: string;
  summary_text?: string;
  summary_sections?: StructuredSummary;
  github_issue_status?: string;
  github_issue_id?: number | null;
  github_issue_url?: string;
  github_issue_detail?: string;
  investigation_id?: number | null;
  technical_report_status?: string;
  technical_report_filename?: string;
  technical_report_path?: string;
  technical_report_preview?: string;
}

export interface InvestigationRun {
  investigation_id: number;
  upload_id: string;
  status: string;
  state: InvestigationState;
}

export interface StructuredSummary {
  headline?: string;
  overview?: string;
  anomalies?: string[];
  historical_matches?: Array<{
    incident_id?: number;
    similarity?: number;
    failure?: string;
    root_cause?: string;
    issue_url?: string;
  }>;
  root_causes?: Array<{
    cause?: string;
    confidence?: number;
    evidence?: string[];
  }>;
  recommendations?: string[];
  action_plan?: string[];
  summary_text?: string;
}
