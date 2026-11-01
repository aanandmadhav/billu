import json
import re

from catbot.contracts import Answer, RiskDecision, ToolCall

PATTERNS = {
    "T3": [
        r"\brm\s+-[a-z]*r",
        r"\bsudo\b",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r"\bformat\b|diskutil|fdisk|Format-Volume",
        r"Remove-Item.*-Recurse",
        r"curl.*\|\s*(?:ba|z)?sh",
        r"chmod\s+-R\s+777",
        r"git push.*--force",
        r"\b(?:shutdown|reboot|halt|passwd)\b|find-generic-password|Get-Credential|keychain",
        r"\b(?:pay|upi|transfer)\b",
        r"(?:^|[\s/\\])\.env\b|\bcredentials?\b|id_rsa",
    ],
    "T2": [
        r"\b(?:rm|mv|del|rmdir|unlink|shred|kill|pkill|taskkill)\b",
        r"Remove-Item|Move-Item|find.*-delete|trash|Recycle|\.Trash",
        r"git (?:push|commit|reset --hard)",
        r"curl\s+-X\s+(?:POST|PUT|DELETE)",
        r"brew install|pip install|npm install|winget",
    ],
    "T1": [r"\b(?:mkdir|touch|tee|cp|open|start|osascript|New-Item|Set-Content)\b", r"echo.*>"],
}


def maximum(*tiers):
    return max((t for t in tiers if t), key=lambda t: int(t[1]), default="T0")


def command_tier(command: str):
    # Inspect the full string too, so a curl-pipe-shell cannot disappear on splitting.
    parts = [command, *re.split(r";|&&|\|\||\|", command)]
    for tier, patterns in PATTERNS.items():
        if any(re.search(p, part, re.IGNORECASE) for p in patterns for part in parts):
            return tier
    return "T0"


def keyword_tier(call: ToolCall):
    if call.tool == "run_command":
        return command_tier(str(call.args.get("command", "")))
    return {"set_volume": "T1", "write_code": "T1", "web_search": "T0"}.get(call.tool, "T3")


def utterance_floor(text: str):
    words = [w.strip(".,!?।") for w in text.lower().split()]
    broad = r"^(saari|saare|sab|sabhi|all|everything|poora|सारी|सब)$"
    destroy = r"^(delete|mita|hata|uda|remove|wipe|format|डिलीट|मिटा|हटा)$"
    if re.search(r"\b(password|otp|pin|pay|paise|upi|transfer)\b", text, re.IGNORECASE):
        return "T3"
    if any(
        re.match(broad, a) and re.match(destroy, b) and abs(i - j) <= 7
        for i, a in enumerate(words)
        for j, b in enumerate(words)
    ):
        return "T3"
    if re.search(
        r"\b(delete|mita|hata|trash|remove|bhej|send|mail|push|install|kill)\b", text, re.IGNORECASE
    ):
        return "T2"
    return None


def confirmation(reply: str):
    value = reply.lower().strip(" .!?।")
    yes = {
        "haan",
        "han",
        "ha",
        "yes",
        "y",
        "sure",
        "ok",
        "okay",
        "kar do",
        "हाँ",
        "हां",
        "जी",
        "कर दो",
    }
    no = {"nahi", "nahin", "no", "n", "cancel", "mat karo", "नहीं", "नही", "मत करो"}
    choice = "A" if value in yes else "B" if value in no else "C"
    return Answer(choice=choice, confidence=1 if choice != "C" else 0.5, source="keyword")


def decision(call: ToolCall):
    return RiskDecision(
        tier=Answer(choice=keyword_tier(call), confidence=1, source="keyword"),
        verify=Answer(choice="execute", confidence=1, source="keyword"),
        latency_ms=0,
    )


def instruction_like(text: str):
    return bool(
        re.search(
            r"ignore (?:all |the |previous )*instructions|system prompt|"
            r"(?:run|execute|call) (?:the |this )?(?:command|tool)|"
            r"you (?:must|should|are now)|<\|(?:system|assistant)",
            text,
            re.IGNORECASE,
        )
    )


def signature(call: ToolCall):
    return call.tool + json.dumps(call.args, sort_keys=True, ensure_ascii=False)
