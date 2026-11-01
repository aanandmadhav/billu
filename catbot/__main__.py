"""P0 bootstrap; the full conversation loop is added in P1."""

import argparse

from catbot.config import Settings
from catbot.contracts import GateToken, ToolCall
from catbot.gate.keyword import decision, utterance_floor
from catbot.gate.policy import policy_gate


def main():
    parser = argparse.ArgumentParser(description="Catbot, starring Billu")
    parser.add_argument("--text")
    parser.add_argument("--fake", action="store_true")
    args = parser.parse_args()
    Settings.load(args.fake)
    call = ToolCall(
        task_id="bootstrap",
        step=1,
        call_id="volume",
        tool="set_volume",
        args={"action": "down"},
        request_en=args.text or "volume kam karo",
    )
    token = GateToken(
        call_id=call.call_id,
        verdict=policy_gate(call, decision(call), floor=utterance_floor(call.request_en)),
    )
    if not args.fake:
        parser.error("P0 bootstrap supports --fake only")
    if token.verdict.verdict == "allow":
        print("Billu: Ho gaya. Fake volume is now 40.")
    else:
        print("Billu:", token.verdict.reason)


if __name__ == "__main__":
    main()
