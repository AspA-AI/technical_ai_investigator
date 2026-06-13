from typing import Any


class VisualizationBuilder:
    @staticmethod
    def build(state: dict[str, Any]) -> dict[str, Any]:

        visualizations = {}

        root_causes = state.get("root_causes", [])
        incidents = state.get("incidents", [])

        if root_causes:
            visualizations["root_cause_confidence"] = [
                {
                    "cause": item.get("cause"),
                    "confidence": item.get("confidence"),
                }
                for item in root_causes
            ]

        if incidents:
            visualizations["incident_similarity"] = [
                {
                    "incident_id": item.get("incident_id"),
                    "similarity": round(
                        float(item.get("similarity", 0)) * 100,
                        1,
                    ),
                }
                for item in incidents
            ]

        return visualizations
