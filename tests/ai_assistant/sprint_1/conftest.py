"""Sprint 1 fixtures: JOBS workload proposal via AI assistant."""
import uuid
import pytest

from tests.ai_assistant.conftest import send_chat_until_proposal


JOBS_PROMPT_PRIMARY = (
    "I need a daily ETL job processing 1TB of data with 4 workers, "
    "running 10 times a day for 30 minutes each"
)

JOBS_PROMPT_FOLLOWUP = (
    "Please configure a Lakeflow Jobs workload for a daily ETL pipeline. "
    "4 workers, runs 10 times per day, each run takes about 30 minutes, "
    "operating 22 days per month. Use serverless if available."
)


@pytest.fixture(scope="module")
def jobs_proposal_result(http_client, test_estimate):
    """
    Send JOBS prompt and return (proposal, response, conversation_id).

    Module-scoped so the expensive AI call is shared across all tests
    in the sprint_1 directory that import this fixture.
    """
    cid = str(uuid.uuid4())
    proposal, response = send_chat_until_proposal(
        http_client,
        messages=[JOBS_PROMPT_PRIMARY, JOBS_PROMPT_FOLLOWUP],
        estimate=test_estimate,
        conversation_id=cid,
    )
    return proposal, response, cid
