export interface CounterfactualParameters {
  temperature_change?: number;
}

export interface WhatIfRequest {
  investigation_id: number;
  parameters: CounterfactualParameters;
}

export interface WhatIfResponse {
  before_risk: string;
  after_risk: string;
  result: { risk_reduction: number };
}
