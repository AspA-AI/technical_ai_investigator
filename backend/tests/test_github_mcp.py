"""Standalone integration test runner for the GitHub Collaboration Tool."""

import sys
from utils.github_client import GitHubCollaborationClient
from config.settings import settings


def run_integration_test():
    print("🚀 [INITIALIZING] Booting GitHub MCP Tool Integration Test...")

    # 1. Print configuration sanity checks (hiding the sensitive token)
    print("\n📋 Checking Environment Configuration:")
    print(f" - Environment: {settings.ENVIRONMENT}")
    print(f" - target Owner: {settings.GITHUB_REPO_OWNER or '❌ MISSING'}")
    print(f" - Target Repo:  {settings.GITHUB_REPO_NAME or '❌ MISSING'}")

    if not settings.GITHUB_TOKEN:
        print("❌ ERROR: GITHUB_TOKEN is empty or missing in your .env file!")
        sys.exit(1)
    else:
        print(f" - Token Status: Loaded (Prefix: {settings.GITHUB_TOKEN[:14]}...)")

    # 2. Instantiate the client using your Pydantic settings pattern
    try:
        print("\n🔧 Instantiating GitHub Collaboration Client...")
        client = GitHubCollaborationClient()
    except Exception as e:
        print(f"❌ Initialization Failed: {str(e)}")
        sys.exit(1)

    # 3. Simulate structured payloads generated from a mock investigation pipeline
    test_asset = "TURBOFAN-UNIT-63"
    test_summary = (
        "Observed high-pressure compressor stall signatures. Standardized "
        "vibration deviations spiked at +4.61 with concurrent high exhaust temperatures "
        "and corresponding RPM drops."
    )
    test_recommendations = [
        "Perform Lockout-Tagout (LOTO) Procedure E-104 on primary fuel links.",
        "Remove high-pressure compressor housing panel cover bolts.",
        "Inspect compressor stator blade clearance tolerances using micrometer gauge.",
        "Check lubrication lines for micro-particulate contamination.",
    ]

    print(
        f"\n📡 Transmitting Live Outbound Payload to GitHub API for asset {test_asset}..."
    )

    # 4. Trigger the live network request
    result = client.create_investigation_issue(
        title=f"🚨 [INTEGRATION TEST] Critical Anomaly Triage: {test_asset}",
        summary=test_summary,
        recommendations=test_recommendations,
    )

    # 5. Output Server Receipts
    print("\n🏁 Network Response Breakdown:")
    if result["status"] == "SUCCESS":
        print("✅ SUCCESS: The request went through flawlessly over the wire!")
        print(f" - Generated Issue Number: #{result['issue_id']}")
        print(f" - Direct Browser URL:      {result['issue_url']}")
        print(f" - API Target Router:       {result['api_route']}")
        print("\n👉 Open that link in your browser to verify the markdown structure!")
    else:
        print("❌ FAILURE: GitHub rejected or missed the request.")
        print(f" - Status Code/Error Class: {result['status']}")
        print(f" - Server Diagnostics:       {result.get('message')}")


if __name__ == "__main__":
    run_integration_test()
