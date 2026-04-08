#!/usr/bin/env python3
"""
smoke_test.py — Quick retrieval regression check for MemPalace.

Ingests a small synthetic dataset into an ephemeral palace, queries it,
and checks that recall meets a minimum threshold. No downloads, no API
keys, runs in seconds.

Usage:
    python -m mempalace.smoke_test
    mempalace benchmark
"""

import sys
import math
import tempfile
import shutil

import chromadb


# -- Synthetic dataset --------------------------------------------------------
# 10 "sessions" with distinct topics, 5 questions with known answers.

SESSIONS = [
    {
        "id": "sess_auth",
        "text": "We decided to migrate authentication from Auth0 to Clerk. Kai recommended it based on pricing and developer experience. The team agreed on 2026-01-15. Maya is handling the migration.",
    },
    {
        "id": "sess_db",
        "text": "Chose Postgres over SQLite for the Orion project because we need concurrent writes and the dataset will exceed 10GB. Decided 2025-11-03.",
    },
    {
        "id": "sess_graphql",
        "text": "Switched the API from REST to GraphQL. Main reasons: reduce over-fetching on mobile clients, and the frontend team already knows Apollo. Took about two weeks to migrate the core endpoints.",
    },
    {
        "id": "sess_cicd",
        "text": "Set up GitHub Actions for CI. Tests run on every PR. Deploy to staging on merge to main. Production deploys are manual via workflow dispatch. Added a Slack notification on failure.",
    },
    {
        "id": "sess_pricing",
        "text": "Decided on a freemium model. Free tier has 1000 requests per month. Pro tier is 29 dollars per month with unlimited requests. Enterprise is custom pricing with SLA.",
    },
    {
        "id": "sess_perf",
        "text": "Found a performance bottleneck in the search endpoint. The N+1 query on user profiles was adding 400ms per request. Fixed with a batch loader. Response time dropped from 600ms to 80ms.",
    },
    {
        "id": "sess_design",
        "text": "Redesigned the dashboard. Moved from a sidebar layout to a top-nav layout. Added dark mode. Riley suggested the color palette. User testing showed 30 percent faster task completion.",
    },
    {
        "id": "sess_security",
        "text": "Security audit results: no critical vulnerabilities. Two medium findings — missing rate limiting on the login endpoint and overly broad CORS headers. Both fixed in the same sprint.",
    },
    {
        "id": "sess_hiring",
        "text": "Interviewing two senior backend candidates next week. Jordan has 8 years experience with distributed systems. Priya has 5 years but strong open source contributions. Decision by Friday.",
    },
    {
        "id": "sess_launch",
        "text": "Launch date set for March 15th. Marketing campaign starts two weeks before. Press embargo lifts on launch day. Ben is coordinating with the press contacts.",
    },
]

QUESTIONS = [
    {
        "query": "Why did we switch to Clerk for authentication?",
        "expected": ["sess_auth"],
    },
    {
        "query": "What database did we choose for Orion?",
        "expected": ["sess_db"],
    },
    {
        "query": "What was the performance problem with search?",
        "expected": ["sess_perf"],
    },
    {
        "query": "What is the pricing model?",
        "expected": ["sess_pricing"],
    },
    {
        "query": "When is the launch date?",
        "expected": ["sess_launch"],
    },
]

# Thresholds
RECALL_AT_1_MIN = 0.8   # 4/5 correct at rank 1
RECALL_AT_3_MIN = 1.0   # 5/5 correct at rank 3


def run_smoke_test(verbose: bool = False) -> dict:
    """
    Run the smoke test. Returns a dict with scores and pass/fail.
    """
    client = chromadb.EphemeralClient()
    try:
        client.delete_collection("smoke_test")
    except Exception:
        pass
    col = client.create_collection("smoke_test")

    # Ingest
    col.add(
        ids=[s["id"] for s in SESSIONS],
        documents=[s["text"] for s in SESSIONS],
    )

    # Query and score
    recall_at_1 = 0
    recall_at_3 = 0
    results_detail = []

    for q in QUESTIONS:
        results = col.query(
            query_texts=[q["query"]],
            n_results=3,
            include=["distances"],
        )
        retrieved_ids = results["ids"][0]
        expected = set(q["expected"])

        hit_at_1 = retrieved_ids[0] in expected
        hit_at_3 = any(rid in expected for rid in retrieved_ids[:3])

        recall_at_1 += float(hit_at_1)
        recall_at_3 += float(hit_at_3)

        results_detail.append({
            "query": q["query"],
            "expected": q["expected"],
            "retrieved": retrieved_ids,
            "hit_at_1": hit_at_1,
            "hit_at_3": hit_at_3,
        })

    n = len(QUESTIONS)
    r1 = recall_at_1 / n
    r3 = recall_at_3 / n

    passed = r1 >= RECALL_AT_1_MIN and r3 >= RECALL_AT_3_MIN

    return {
        "recall_at_1": r1,
        "recall_at_3": r3,
        "threshold_r1": RECALL_AT_1_MIN,
        "threshold_r3": RECALL_AT_3_MIN,
        "passed": passed,
        "questions": n,
        "details": results_detail,
    }


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print()
    print("=" * 55)
    print("  MemPalace — Retrieval Smoke Test")
    print("=" * 55)
    print()
    print("  Testing core retrieval pipeline against synthetic data...")
    print()

    result = run_smoke_test(verbose=verbose)

    for d in result["details"]:
        status = "PASS" if d["hit_at_3"] else "FAIL"
        rank1 = "rank-1" if d["hit_at_1"] else "       "
        print(f"  [{status}] {rank1}  {d['query']}")
        if verbose or not d["hit_at_3"]:
            print(f"           expected: {d['expected']}")
            print(f"           got:      {d['retrieved']}")

    print()
    print(f"  Recall@1:  {result['recall_at_1']:.0%}  (threshold: {result['threshold_r1']:.0%})")
    print(f"  Recall@3:  {result['recall_at_3']:.0%}  (threshold: {result['threshold_r3']:.0%})")
    print()

    if result["passed"]:
        print("  RESULT: PASS — retrieval pipeline is healthy")
    else:
        print("  RESULT: FAIL — retrieval quality has regressed")

    print()
    print("=" * 55)
    print()

    if not result["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
