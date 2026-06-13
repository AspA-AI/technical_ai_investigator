"""Phase 5 & 6 Integration Test: Archiving a Completed GitHub Issue Thread."""

import sys
from database.session import SessionLocal
from database.session import init_db
from vectorstore.incident_store import IncidentVectorStore
from utils.logger import setup_logging, get_logger

# 1. Initialize custom terminal log category mappings
setup_logging(debug=True)
log = get_logger("tests.github_archive")


def run_closure_archival_test():
    log.service("🚀 Starting Phase 5 & 6 Asynchronous Archival Integration Test...")

    # 2. Open our connection session
    db = SessionLocal()
    try:
        # Use the normal backend bootstrap so pgvector is installed first.
        init_db()

        # Now proceed with your store initialization
        store = IncidentVectorStore(db)

        # 3. Simulated GitHub payload captured upon an issue 'closed' webhook event
        mock_github_issue_payload = {
            "number": 1,
            "html_url": "https://github.com/RYees/factory-maintenance-tracking/issues/1",
            "created_at": "2026-06-12T14:30:00Z",
            "closed_at": "2026-06-12T22:15:00Z",
        }

        # 4. Chronological comment ledger collected right before archiving
        mock_technician_comments = [
            {
                "user": {"login": "rzapp"},
                "body": "Initial automated triage looks solid. Commencing structural physical analysis on Conveyor Line 2.",
                "created_at": "2026-06-12T15:20:00Z",
            },
            {
                "user": {"login": "senior_tech_bob"},
                "body": "Brainstormed about pressure line issues, but that was a false path. Discovered massive bearing assembly scoring upon housing cover removal.",
                "created_at": "2026-06-12T18:45:00Z",
            },
            {
                "user": {"login": "rzapp"},
                "body": "Replaced bearing housing assembly and recalibrated RPM levels. System stabilizing cleanly. Closing ticket.",
                "created_at": "2026-06-12T22:10:00Z",
            },
        ]

        target_incident_id = 1002
        sensor_context = "Standardized vibration profiles spiked to +4.61 with parallel RPM degradation drops."
        ai_hypothesis = "Suspected mechanical bearing friction degradation or housing structural misalignment."

        log.tool(
            f"Processing incident ID {target_incident_id} through vector embedding layer..."
        )

        # 5. Execute the storage method we added to your IncidentVectorStore class
        archived_incident = store.archive_closed_github_issue(
            incident_id=target_incident_id,
            issue_data=mock_github_issue_payload,
            comments=mock_technician_comments,
            sensor_summary=sensor_context,
            initial_ai_hypothesis=ai_hypothesis,
        )

        log.db("🏁 POSTGRESQL TRANSACTION SUCCESSFUL")
        log.info(f" -> Bound ID:       {archived_incident.incident_id}")
        log.info(f" -> Outage Status:  {archived_incident.failure}")
        log.info(f" -> Resolution Ref: {archived_incident.resolution}")
        log.info(
            f" -> Vector Layout:  {len(archived_incident.embedding)} indices stored."
        )

        print("\n" + "=" * 60)
        print("🔍 COMPILED SUMMARY_TEXT STORED IN DATABASE FIELD:")
        print("=" * 60)
        print(archived_incident.summary_text)
        print("=" * 60 + "\n")

        log.service("✅ Phase 5 & 6 Verification Completed: Data is safely indexed.")

    except Exception as e:
        log.exception(f"❌ Verification script failed: {str(e)}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run_closure_archival_test()
