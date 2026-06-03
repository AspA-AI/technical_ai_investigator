from pydantic import BaseModel

from api.schemas.tools import CounterfactualInputSchema, CounterfactualOutputSchema


class WhatIfRequest(BaseModel):
    investigation_id: int
    parameters: CounterfactualInputSchema


class WhatIfResponse(BaseModel):
    before_risk: str
    after_risk: str
    result: CounterfactualOutputSchema
