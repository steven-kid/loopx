from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from loopx.benchmark_core.loop_protocol import (
    CODEX_CLI_GOAL_BASELINE_ROUTE,
    LOOPX_GOAL_START_PRODUCT_MODE_ROUTE,
    MATCHED_PAIR_CONTRACT_SCHEMA_VERSION,
    SCORED_GOAL_PROOF_SCHEMA_VERSION,
    SCORED_GOAL_PROOF_SOURCE,
)


SKILLSBENCH_MATCHED_PAIR_PRODUCER_SCHEMA_VERSION = (
    "skillsbench_matched_pair_producer_v0"
)
SKILLSBENCH_MATCHED_ROUTES = frozenset(
    {
        CODEX_CLI_GOAL_BASELINE_ROUTE,
        LOOPX_GOAL_START_PRODUCT_MODE_ROUTE,
    }
)


def _safe_text(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _positive_int(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return 0


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _network_policy_fingerprint(config: Mapping[str, Any]) -> str:
    codex_mode = _safe_text(
        config.get("codex_api_egress_mode_resolved"),
        limit=80,
    )
    benchmark_mode = _safe_text(
        config.get("benchmark_egress_proxy_mode_effective")
        or config.get("benchmark_egress_proxy_mode_requested"),
        limit=80,
    )
    if not codex_mode or not benchmark_mode:
        return ""
    return _canonical_digest(
        {
            "codex_api_egress_mode": codex_mode,
            "benchmark_egress_proxy_mode": benchmark_mode,
        }
    )


def skillsbench_task_packet_fingerprint(
    *,
    benchmark_id: str,
    case_ids: list[str],
    instruction: str,
) -> str:
    return _canonical_digest(
        {
            "benchmark_id": _safe_text(benchmark_id, limit=80),
            "case_ids": [_safe_text(case_id, limit=120) for case_id in case_ids],
            "instruction_sha256": hashlib.sha256(instruction.encode()).hexdigest(),
        }
    )


def skillsbench_scored_goal_trace_satisfied(
    goal_trace: Mapping[str, Any] | None,
) -> bool:
    trace = dict(goal_trace or {})
    return bool(
        trace.get("goal_get_present") is True
        and trace.get("turn_id_present") is True
        and trace.get("scored_goal_proof_source") == SCORED_GOAL_PROOF_SOURCE
    )


def build_skillsbench_scored_goal_proof(
    *,
    route: str,
    runner_prerequisites: Mapping[str, Any] | None,
) -> dict[str, Any]:
    prerequisites = dict(runner_prerequisites or {})
    goal_get_present = prerequisites.get("goal_get_present") is True
    turn_id_present = prerequisites.get("turn_id_present") is True
    proof_source = _safe_text(
        prerequisites.get("scored_goal_proof_source"),
        limit=120,
    )
    proof_required = route == CODEX_CLI_GOAL_BASELINE_ROUTE
    proof_satisfied = bool(
        not proof_required
        or (
            goal_get_present
            and turn_id_present
            and proof_source == SCORED_GOAL_PROOF_SOURCE
        )
    )
    return {
        "schema_version": SCORED_GOAL_PROOF_SCHEMA_VERSION,
        "route": _safe_text(route, limit=120),
        "required": proof_required,
        "satisfied": proof_satisfied,
        "goal_get_present": goal_get_present,
        "turn_id_present": turn_id_present,
        "proof_source": proof_source,
        "tui_marker_only": bool(
            prerequisites.get("codex_cli_goal_tui_trace_present") is True
            and not proof_satisfied
        ),
        "first_blocker": (
            ""
            if proof_satisfied
            else "scored_codex_cli_goal_persistent_proof_missing"
        ),
        "raw_transcript_recorded": False,
        "raw_session_state_recorded": False,
        "credentials_recorded": False,
        "local_paths_recorded": False,
    }


def build_skillsbench_matched_pair_contract(
    *,
    route: str,
    runner_config: Mapping[str, Any],
    runner_prerequisites: Mapping[str, Any] | None,
    task_packet_fingerprint: str,
) -> dict[str, Any]:
    config = dict(runner_config)
    prerequisites = dict(runner_prerequisites or {})
    benchmark_id = _safe_text(config.get("benchmark_id"), limit=80)
    task_id = _safe_text(config.get("task_id"), limit=120)
    model = _safe_text(config.get("model"), limit=80)
    reasoning_effort = _safe_text(
        config.get("reasoning_effort")
        or config.get("codex_cli_reasoning_effort"),
        limit=40,
    )
    runner_commit = _safe_text(
        prerequisites.get("loopx_runner_source_git_head"),
        limit=40,
    )
    proof = build_skillsbench_scored_goal_proof(
        route=route,
        runner_prerequisites=prerequisites,
    )
    contract = {
        "schema_version": MATCHED_PAIR_CONTRACT_SCHEMA_VERSION,
        "case_set_fingerprint": _canonical_digest([task_id]) if task_id else "",
        "case_order_fingerprint": _canonical_digest([task_id]) if task_id else "",
        "model": model,
        "reasoning_effort": reasoning_effort,
        "task_packet_fingerprint": _safe_text(
            task_packet_fingerprint,
            limit=80,
        ),
        "instruction_channel": _safe_text(
            prerequisites.get("matched_instruction_channel"),
            limit=120,
        ),
        "sandbox_policy": _safe_text(config.get("sandbox"), limit=80),
        "network_policy": _network_policy_fingerprint(config),
        "outer_timeout_sec": _positive_int(config.get("outer_timeout_sec")),
        "token_budget": _positive_int(
            prerequisites.get("matched_token_budget")
        ),
        "runner_commit": runner_commit,
        "reducer_commit": runner_commit,
        "official_verifier_closeout_contract": _safe_text(
            prerequisites.get("official_verifier_closeout_contract"),
            limit=120,
        ),
        "best_of_retry_replacement": bool(
            prerequisites.get("independent_goal_best_of_retry_replacement")
        ),
        "symmetric_infra_exclusion": (
            prerequisites.get("symmetric_infra_exclusion") is True
        ),
    }
    missing_fields = [
        field
        for field, value in contract.items()
        if field != "schema_version"
        and not isinstance(value, bool)
        and value in {"", 0}
    ]
    blockers = [f"{field}_missing" for field in missing_fields]
    if route not in SKILLSBENCH_MATCHED_ROUTES:
        blockers.append("route_not_in_skillsbench_matched_pair")
    if proof.get("satisfied") is not True:
        blockers.append(str(proof.get("first_blocker") or "goal_proof_missing"))
    if contract["best_of_retry_replacement"] is not False:
        blockers.append("best_of_retry_replacement_not_disabled")
    if contract["symmetric_infra_exclusion"] is not True:
        blockers.append("symmetric_infra_exclusion_not_confirmed")
    return {
        **contract,
        "producer_schema_version": SKILLSBENCH_MATCHED_PAIR_PRODUCER_SCHEMA_VERSION,
        "benchmark_id": benchmark_id,
        "route": _safe_text(route, limit=120),
        "ready": not blockers,
        "blockers": blockers,
        "scored_goal_proof": proof,
        "raw_task_text_recorded": False,
        "raw_verifier_output_recorded": False,
        "raw_trajectory_recorded": False,
        "raw_logs_recorded": False,
        "credentials_recorded": False,
        "local_paths_recorded": False,
    }
