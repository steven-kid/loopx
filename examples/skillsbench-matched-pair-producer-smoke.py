#!/usr/bin/env python3
"""Smoke-test public-safe SkillsBench matched-pair evidence production."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from loopx.benchmark_adapters.skillsbench_matched_pair import (  # noqa: E402
    build_skillsbench_matched_pair_contract,
    build_skillsbench_scored_goal_proof,
    skillsbench_scored_goal_trace_satisfied,
    skillsbench_task_packet_fingerprint,
)
from loopx.benchmark_core.loop_protocol import (  # noqa: E402
    CODEX_CLI_GOAL_BASELINE_ROUTE,
    LOOPX_GOAL_START_PRODUCT_MODE_ROUTE,
)


def _runner_config() -> dict[str, object]:
    return {
        "benchmark_id": "skillsbench@1.1",
        "task_id": "public-fixture-case",
        "model": "gpt-fixture",
        "reasoning_effort": "xhigh",
        "sandbox": "docker",
        "outer_timeout_sec": 21600,
        "codex_api_egress_mode_resolved": "direct",
        "benchmark_egress_proxy_mode_requested": "off",
    }


def _complete_prerequisites() -> dict[str, object]:
    return {
        "loopx_runner_source_git_head": "abc123",
        "matched_instruction_channel": "skillsbench_private_packet_v1",
        "matched_token_budget": 200000,
        "official_verifier_closeout_contract": (
            "skillsbench_benchflow_official_result_v1"
        ),
        "symmetric_infra_exclusion": True,
        "independent_goal_best_of_retry_replacement": False,
        "goal_get_present": True,
        "turn_id_present": True,
        "scored_goal_proof_source": (
            "codex_app_server_thread_goal_get_turn_start"
        ),
    }


def test_private_instruction_fingerprint_is_stable() -> None:
    instruction = "private fixture instruction"
    expected = skillsbench_task_packet_fingerprint(
        benchmark_id="skillsbench@1.1",
        case_ids=["public-fixture-case"],
        instruction=instruction,
    )
    repeated = skillsbench_task_packet_fingerprint(
        benchmark_id="skillsbench@1.1",
        case_ids=["public-fixture-case"],
        instruction=instruction,
    )
    changed = skillsbench_task_packet_fingerprint(
        benchmark_id="skillsbench@1.1",
        case_ids=["public-fixture-case"],
        instruction=instruction + " changed",
    )
    assert expected == repeated
    assert expected != changed
    assert instruction not in expected


def test_tui_marker_does_not_impersonate_goal_proof() -> None:
    proof = build_skillsbench_scored_goal_proof(
        route=CODEX_CLI_GOAL_BASELINE_ROUTE,
        runner_prerequisites={"codex_cli_goal_tui_trace_present": True},
    )
    assert proof["satisfied"] is False
    assert proof["tui_marker_only"] is True
    assert proof["first_blocker"] == (
        "scored_codex_cli_goal_persistent_proof_missing"
    )
    booleans_without_source = build_skillsbench_scored_goal_proof(
        route=CODEX_CLI_GOAL_BASELINE_ROUTE,
        runner_prerequisites={
            "goal_get_present": True,
            "turn_id_present": True,
        },
    )
    assert booleans_without_source["satisfied"] is False


def test_scored_goal_proof_must_be_atomic_within_one_trace() -> None:
    goal_only = {
        "goal_get_present": True,
        "turn_id_present": False,
        "scored_goal_proof_source": (
            "codex_app_server_thread_goal_get_turn_start"
        ),
    }
    turn_only = {
        "goal_get_present": False,
        "turn_id_present": True,
        "scored_goal_proof_source": (
            "codex_app_server_thread_goal_get_turn_start"
        ),
    }
    complete = {
        "goal_get_present": True,
        "turn_id_present": True,
        "scored_goal_proof_source": (
            "codex_app_server_thread_goal_get_turn_start"
        ),
    }
    assert skillsbench_scored_goal_trace_satisfied(goal_only) is False
    assert skillsbench_scored_goal_trace_satisfied(turn_only) is False
    assert skillsbench_scored_goal_trace_satisfied(complete) is True
    assert skillsbench_scored_goal_trace_satisfied(
        {**complete, "scored_goal_proof_source": "unrelated_goal_probe"}
    ) is False


def test_complete_contract_is_ready_and_missing_policy_fails_closed() -> None:
    fingerprint = skillsbench_task_packet_fingerprint(
        benchmark_id="skillsbench@1.1",
        case_ids=["public-fixture-case"],
        instruction="private fixture instruction",
    )
    baseline = build_skillsbench_matched_pair_contract(
        route=CODEX_CLI_GOAL_BASELINE_ROUTE,
        runner_config=_runner_config(),
        runner_prerequisites=_complete_prerequisites(),
        task_packet_fingerprint=fingerprint,
    )
    treatment = build_skillsbench_matched_pair_contract(
        route=LOOPX_GOAL_START_PRODUCT_MODE_ROUTE,
        runner_config=_runner_config(),
        runner_prerequisites={
            key: value
            for key, value in _complete_prerequisites().items()
            if key not in {"goal_get_present", "turn_id_present"}
        },
        task_packet_fingerprint=fingerprint,
    )
    assert baseline["ready"] is True, baseline
    assert treatment["ready"] is True, treatment
    assert baseline["task_packet_fingerprint"] == treatment[
        "task_packet_fingerprint"
    ]
    assert baseline["raw_task_text_recorded"] is False
    missing = build_skillsbench_matched_pair_contract(
        route=CODEX_CLI_GOAL_BASELINE_ROUTE,
        runner_config={
            key: value
            for key, value in _runner_config().items()
            if key != "benchmark_egress_proxy_mode_requested"
        },
        runner_prerequisites={"codex_cli_goal_tui_trace_present": True},
        task_packet_fingerprint=fingerprint,
    )
    assert missing["ready"] is False
    assert "network_policy_missing" in missing["blockers"]
    assert "scored_codex_cli_goal_persistent_proof_missing" in missing["blockers"]
    assert "symmetric_infra_exclusion_not_confirmed" in missing["blockers"]


def _function_source(source: str, name: str) -> str:
    match = re.search(
        rf"^def {re.escape(name)}\b.*?(?=^def |\Z)",
        source,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, name
    return match.group(0)


def test_runner_wiring_is_fail_closed_and_public_safe() -> None:
    runner_path = REPO_ROOT / "scripts" / "skillsbench_automation_loop.py"
    source = runner_path.read_text(encoding="utf-8")
    record = _function_source(source, "_record_matched_task_packet_fingerprint")
    assert "skillsbench_task_packet_fingerprint(" in record
    assert 'trace["matched_task_packet_raw_text_recorded"] = False' in record
    assert 'prerequisites["matched_task_packet_raw_text_recorded"] = False' in record
    assert "instruction=" in record
    assert "raw_task_text" not in record

    merge = _function_source(source, "_merge_host_local_acp_relay_trace_summary")
    assert "skillsbench_scored_goal_trace_satisfied(goal_trace)" in merge
    assert "codex_cli_scored_goal_proof_present" in merge
    assert "codex_cli_goal_get_present" not in merge
    assert "codex_cli_turn_id_present" not in merge
    assert 'prerequisites["goal_get_present"]' in merge
    assert 'prerequisites["turn_id_present"]' in merge
    assert 'prerequisites["scored_goal_proof_source"]' in merge

    countability = _function_source(
        source,
        "_apply_codex_cli_goal_countability_guard_attribution",
    )
    assert "persistent_goal_proof_present" in countability
    assert "skillsbench_codex_cli_goal_persistent_proof_missing" in countability

    reducer = _function_source(source, "reduce_result")
    assert 'compact["matched_pair_contract"] = matched_pair_contract' in reducer
    assert 'compact["scored_goal_proof"] = scored_goal_proof' in reducer


def main() -> int:
    test_private_instruction_fingerprint_is_stable()
    test_tui_marker_does_not_impersonate_goal_proof()
    test_scored_goal_proof_must_be_atomic_within_one_trace()
    test_complete_contract_is_ready_and_missing_policy_fails_closed()
    test_runner_wiring_is_fail_closed_and_public_safe()
    print("skillsbench-matched-pair-producer-smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
