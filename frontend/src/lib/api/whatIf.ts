import { apiClient } from "./client";
import type { WhatIfRequest, WhatIfResponse } from "../../types/whatIf";

export async function runWhatIfAnalysis(
  body: WhatIfRequest
): Promise<WhatIfResponse> {
  const { data } = await apiClient.post<WhatIfResponse>(
    "/api/investigations/what-if",
    body
  );
  return data;
}
