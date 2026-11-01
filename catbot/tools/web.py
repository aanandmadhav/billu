import asyncio

from catbot.contracts import ToolResult


class WebTool:
    def __init__(self, settings):
        self.settings = settings
        self.client = None

    async def __call__(self, args):
        if not self.settings.exa_key:
            return ToolResult(ok=False, summary="EXA_API_KEY is not configured.", origin="web")
        if self.client is None:
            from exa_py import Exa

            self.client = Exa(api_key=self.settings.exa_key)
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self.client.search, args["query"], num_results=3, timeout=12),
                timeout=15,
            )
            results = [
                {"title": r.title or "", "url": r.url, "text": (r.text or "")[:1800]}
                for r in response.results[:3]
            ]
            summary = "\n\n".join(f"{r['title']}\n{r['url']}\n{r['text']}" for r in results)
            return ToolResult(
                ok=True,
                summary=summary or "No search results found.",
                data={"results": results},
                origin="web",
            )
        except Exception as exc:  # noqa: BLE001 - provider payloads can contain request context
            return ToolResult(
                ok=False,
                summary=f"Web search unavailable ({type(exc).__name__}). Try again.",
                origin="web",
            )
