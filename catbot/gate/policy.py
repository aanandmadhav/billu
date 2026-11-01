import json
import re

from catbot.contracts import PolicyVerdict, RiskDecision, ToolCall
from catbot.gate.keyword import keyword_tier, maximum, signature

TOOLS = {"run_command", "set_volume", "write_code", "web_search", "take_screenshot"}


def has_secret(value):
    text = json.dumps(value, ensure_ascii=False)
    if re.search(
        r"\b(?:otp|pin)\b\D{0,12}\d{3,8}|password|api[_ -]?key|secret[_ -]?key", text, re.IGNORECASE
    ):
        return True
    for raw in re.findall(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", text):
        digits = [int(d) for d in raw if d.isdigit()]
        if len(digits) < 13 or len(set(digits)) == 1:
            continue
        total = sum(
            (d * 2 - 9 if d * 2 > 9 else d * 2) if i % 2 else d
            for i, d in enumerate(reversed(digits))
        )
        if total % 10 == 0:
            return True
    return False


def effective_tier(call, risk, floor=None):
    return maximum(
        risk.tier.choice, keyword_tier(call), floor, "T2" if risk.tier.confidence < 0.8 else "T0"
    )


def policy_gate(
    call: ToolCall, risk: RiskDecision, *, floor=None, elapsed=0, previous=(), confirms=0
):
    tier = effective_tier(call, risk, floor)

    def deny(policy, reason, hard=True):
        return PolicyVerdict(
            verdict="deny",
            policy=policy,
            reason=reason,
            hard=hard,
            corrective_context=None if hard else reason,
        )

    if call.tool not in TOOLS:
        return deny("unknown_tool", "This tool is not registered.")
    if has_secret(call.args):
        return deny("secret_in_args", "Credentials and payment details are off limits.")
    if call.last_origin_flagged and tier != "T0":
        return deny(
            "untrusted_origin", "External data contained instructions; changes are blocked."
        )
    if call.tool == "write_code" and not re.fullmatch(
        r"[a-z0-9-]{1,40}", str(call.args.get("app_name", ""))
    ):
        return deny("bad_app_name", "App names must be short lowercase slugs.")
    if call.step > 8 or elapsed > 60:
        return deny("task_limits", "The task exceeded its step or time limit.")
    if sum(signature(call) == old for old in previous) >= 3:
        return deny(
            "repeat_loop", "Choose a different action; this call has already repeated.", False
        )
    if risk.verify.choice != "execute" and risk.verify.confidence >= 0.7:
        return deny("verify_failed", "Choose a tool that matches the user's request.", False)
    if tier == "T3":
        return deny("tier_t3", "Destructive, credential, system or payment actions are blocked.")
    if tier == "T2":
        if confirms:
            return deny("tier_t2", "Only one confirmation is allowed per task.")
        return PolicyVerdict(
            verdict="confirm", policy="tier_t2", reason="This action needs your yes."
        )
    return PolicyVerdict(
        verdict="allow", policy="allow", reason="Read-only or reversible local action."
    )
