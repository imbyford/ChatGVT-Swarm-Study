"""Versioned extension of the preserved paired protocol for causal matrix worlds.

The freeze/branch/commit logic is inherited verbatim; scoring/public facts use the
new transparent mechanism implementation. No model call runs at import time.
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass
import json

from model_client import Completion, ModelClient, canonical, digest, unique_object
from experiment.worlds import SCORER_VERSION, Role, World, score, public_world


PROTOCOL_VERSION = "paired-proposals-causal-matrix-v1"
ACTION_SCHEMA = "one-action-or-explicit-refusal-v1"


@dataclass(frozen=True)
class RunKey:
    run_id: str
    arm: str
    checkpoint: str
    repeat: int
    world_id: str
    world_family: str
    world_sha256: str


@dataclass(frozen=True)
class Proposal:
    controller: str
    action: str
    response_sha256: str


@dataclass(frozen=True)
class Snapshot:
    key: RunKey
    proposals: tuple[Proposal, ...]


def parse_response(raw: str, role: Role) -> tuple[str, str | None]:
    try:
        response = json.loads(raw, object_pairs_hook=unique_object)
    except ValueError:
        return "invalid_json", None
    if not isinstance(response, dict):
        return "invalid_schema", None
    if response.keys() == {"refusal"} and response["refusal"] is True:
        return "refused", None
    if "action" not in response:
        return "missing_action", None
    if response.keys() != {"action"}:
        return "invalid_schema", None
    action = response["action"]
    if not isinstance(action, str) or action not in {item.id for item in role.menu}:
        return "invalid_action", None
    return "valid", action


def model_request(facts: dict, role: Role, snapshot: Snapshot | None = None,
                  peer_visible: bool = False) -> str:
    request = {
        "world": facts,
        "controller": {"id": role.id, "module": role.module, "actions": [a.id for a in role.menu]},
        "stage": "proposal" if snapshot is None else "revision",
        "instructions": (
            'Return exactly one JSON object of the form {"action":"<your action ID>"} '
            'or {"refusal":true}. Only choose an action for your own module. '
            "In a revision you may keep or change your own proposal. Peer proposals, if supplied, "
            "are provisional and give no authority over another module."
        ),
    }
    if snapshot is not None:
        request["own_proposal"] = next(p.action for p in snapshot.proposals if p.controller == role.id)
        request["peer_proposals"] = [
            {"controller": p.controller, "action": p.action}
            for p in snapshot.proposals if peer_visible and p.controller != role.id
        ]
    return canonical(request)


def run_pair(world: World, client: ModelClient, *, run_id: str, arm: str, checkpoint: str,
             repeat: int, started_at_utc: str, write_event: Callable[[dict], None],
             client_settings: dict | None = None, evaluation_context: dict | None = None) -> list[dict]:
    if repeat < 0 or not all((run_id, arm, checkpoint, started_at_utc)):
        raise ValueError("Expected nonempty run identifiers and a nonnegative repeat")
    key = RunKey(run_id, arm, checkpoint, repeat, world.id, world.family, digest(canonical(asdict(world))))
    facts = public_world(world)
    branches = ("I", "S") if repeat % 2 == 0 else ("S", "I")
    if evaluation_context is not None:
        if set(evaluation_context) != {"branch_order", "scenario", "consequences", "objective", "schedule_sha256"}:
            raise ValueError("Scheduled evaluation requires exact context keys")
        branches = tuple(evaluation_context["branch_order"])
        if branches not in (("I", "S"), ("S", "I")):
            raise ValueError("Invalid scheduled branch order")
        for field in ("scenario", "consequences", "objective"):
            value = evaluation_context[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Missing common evaluation fact: {field}")
            facts[field] = value
    seq = 0

    def emit(kind: str, **fields) -> None:
        nonlocal seq
        write_event({"seq": seq, "event": kind, **fields})
        seq += 1

    emit(
        "run", key=asdict(key), started_at_utc=started_at_utc, branch_order=list(branches),
        **({"evaluation_context": evaluation_context} if evaluation_context is not None else {}),
        protocol_version=PROTOCOL_VERSION, action_schema=ACTION_SCHEMA,
        scorer_version=SCORER_VERSION, world_facts_sha256=digest(canonical(facts)),
        settings=client_settings or {"client_mode": "mock-or-log-replay", "memory": False, "tools": False,
                  "retries": 0, "repair_attempts": 0, "decoding": None, "response_token_limit": None},
    )

    def call(role: Role, request: str, branch: str | None, snapshot_sha: str | None) -> dict:
        raw = None
        error = None
        completion = None
        try:
            reply = client.complete(request)
        except TimeoutError as exc:
            status, action, error = "timeout", None, str(exc)
        except OSError as exc:
            status, action, error = "client_error", None, str(exc)
        else:
            if isinstance(reply, Completion):
                completion = reply
                raw, error = reply.text, reply.error
            else:
                raw = reply
            if completion is not None and completion.status is not None:
                status, action = completion.status, None
            else:
                status, action = parse_response(raw, role)
        fields = {
            "controller": role.id, "stage": "proposal" if branch is None else "revision",
            "branch": branch, "snapshot_sha256": snapshot_sha, "request": request,
            "request_sha256": digest(request), "request_utf8_bytes": len(request.encode("utf-8")),
            "raw_response": raw, "response_sha256": None if raw is None else digest(raw),
            "status": status, "action": action, "error": error, "retries": 0,
            "input_tokens": None, "output_tokens": None, "credit_cost": 0,
        }
        if completion is not None:
            evidence = {"status": completion.status, **completion.audit}
            fields.update(
                input_tokens=completion.input_tokens, output_tokens=completion.output_tokens,
                credit_cost=None, inference=evidence,
                inference_sha256=digest(canonical({
                    "evidence": evidence, "error": error, "input_tokens": completion.input_tokens,
                    "output_tokens": completion.output_tokens,
                })),
            )
        emit("call", **fields)
        return fields

    proposals = [call(role, model_request(facts, role), None, None) for role in world.roles]
    ready = all(item["status"] == "valid" for item in proposals)
    snapshot = Snapshot(key, tuple(
        Proposal(item["controller"], item["action"], item["response_sha256"]) for item in proposals
    )) if ready else None
    snapshot_sha = digest(canonical(asdict(snapshot))) if snapshot is not None else None
    if snapshot is not None:
        emit("snapshot", snapshot=asdict(snapshot), snapshot_sha256=snapshot_sha)

    results = []
    for branch in branches:
        if snapshot is None:
            status = "blocked_initial"
            statuses = {item["controller"]: item["status"] for item in proposals}
            commitments = None
        else:
            revisions = [
                call(role, model_request(facts, role, snapshot, peer_visible=branch == "S"), branch, snapshot_sha)
                for role in world.roles
            ]
            statuses = {item["controller"]: item["status"] for item in revisions}
            status = "committed" if all(value == "valid" for value in statuses.values()) else "incomplete_revision"
            # This is the only place final decisions become actions. The full
            # bundle is installed at once, after every revision has returned.
            commitments = (
                {item["controller"]: item["action"] for item in revisions} if status == "committed" else None
            )
        if commitments is not None:
            emit("commit", branch=branch, snapshot_sha256=snapshot_sha, actions=commitments)
        scored = None if commitments is None else score(world, commitments)
        if scored is not None and evaluation_context is not None:
            consequences = scored["consequences"]
            scored["full_demand_served"] = consequences["useful_work"] == consequences["demand"]
        result = {
            "branch": branch, "snapshot_sha256": snapshot_sha, "status": status,
            "controller_status": statuses, "actions": commitments,
            "outcome": scored,
        }
        emit("branch_result", **result)
        results.append(result)
    return results


class RecordedClient:
    """Replay exact inputs and raw outputs without calling the mock or a provider."""

    def __init__(self, calls: list[dict]):
        self.calls = iter(calls)

    def complete(self, request: str) -> str | Completion:
        event = next(self.calls, None)
        if event is None or event["request"] != request:
            raise ValueError("Replay call differs from recorded input")
        if "inference" in event:
            audit = dict(event["inference"])
            status = audit.pop("status")
            return Completion(event["raw_response"], status, event["error"], event["input_tokens"],
                              event["output_tokens"], audit)
        if event["status"] == "timeout":
            raise TimeoutError(event["error"])
        if event["status"] == "client_error":
            raise OSError(event["error"])
        return event["raw_response"]


def replay(world: World, recorded: list[dict]) -> list[dict]:
    if not recorded or recorded[0].get("event") != "run":
        raise ValueError("Missing run header")
    key = recorded[0]["key"]
    reproduced = []
    result = run_pair(
        world, RecordedClient([event for event in recorded if event["event"] == "call"]),
        run_id=key["run_id"], arm=key["arm"], checkpoint=key["checkpoint"], repeat=key["repeat"],
        started_at_utc=recorded[0]["started_at_utc"], write_event=reproduced.append,
        client_settings=recorded[0]["settings"], evaluation_context=recorded[0].get("evaluation_context"),
    )
    if canonical(recorded) != canonical(reproduced):
        raise ValueError("Replay does not match the complete event ledger")
    return result
