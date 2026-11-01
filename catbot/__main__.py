import argparse
import asyncio

from catbot.config import Settings
from catbot.loop import Runner


async def text_mode(settings, args):
    async def confirmer(task_id, question):
        if args.yes:
            return "haan"
        if args.no:
            return "nahi"
        return await asyncio.to_thread(input, "Billu needs an answer (haan/nahi): ")

    runner = Runner(settings, confirmer=confirmer)

    async def payment_reader():
        if args.treat:
            return "chai"
        return await asyncio.to_thread(
            input, "Billu wants chai. Type chai or press Enter to wait: "
        )

    runner.payment_reader = payment_reader
    runner.start()
    queue = runner.bus.subscribe()

    async def display():
        while True:
            event = await queue.get()
            if event.stage in {"speak", "bubble"}:
                print("Billu:", event.payload["text"], flush=True)
            elif event.stage in {"gate", "code"}:
                print(event.stage + ":", event.payload, flush=True)

    printer = asyncio.create_task(display())
    try:
        await runner.run(args.text)
        if runner.code.busy:
            await runner.code.task
        await asyncio.sleep(0.01)
    finally:
        printer.cancel()
        await asyncio.gather(printer, return_exceptions=True)
        runner.bus.unsubscribe(queue)
        await runner.close()


def main():
    parser = argparse.ArgumentParser(description="Catbot, starring Billu the Delhi street cat")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--text", help="Give Billu a text command")
    mode.add_argument(
        "--serve", action="store_true", help="Open the local voice and decision dashboard"
    )
    mode.add_argument("--desktop", action="store_true", help="Backend managed by the Electron app")
    parser.add_argument(
        "--fake", action="store_true", help="In-memory demo; no real services or desktop actions"
    )
    parser.add_argument("--treat", action="store_true", help="Give Billu chai for the demo tease")
    answer = parser.add_mutually_exclusive_group()
    answer.add_argument(
        "--yes", action="store_true", help="Answer this task's single confirmation with yes"
    )
    answer.add_argument(
        "--no", action="store_true", help="Answer this task's single confirmation with no"
    )
    args = parser.parse_args()
    settings = Settings.load(args.fake)
    if args.serve or args.desktop:
        import uvicorn

        from catbot.server import create_app

        if args.desktop:
            if not settings.desktop_token:
                parser.error("--desktop is managed by the Electron app; use npm start")
            import json
            import socket

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", 0))
                print("CATBOT_READY " + json.dumps({"port": sock.getsockname()[1]}), flush=True)
                config = uvicorn.Config(
                    create_app(settings), host="127.0.0.1", log_level="warning", access_log=False
                )
                uvicorn.Server(config).run(sockets=[sock])
        else:
            uvicorn.run(create_app(settings), host="127.0.0.1", port=settings.port)
    else:
        asyncio.run(text_mode(settings, args))


if __name__ == "__main__":
    main()
