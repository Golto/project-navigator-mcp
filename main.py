import sys
from app import get_mcp
from app.mcp import configure

TRANSPORTS = ("stdio", "sse")

def main() -> None:
    transport = "stdio"
    host = "0.0.0.0"
    port = 8002

    for arg in sys.argv[1:]:
        if arg.startswith("--transport="):
            transport = arg.split("=", 1)[1]
        elif arg.startswith("--host="):
            host = arg.split("=", 1)[1]
        elif arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])

    if transport not in TRANSPORTS:
        print(f"Usage: main.py [--transport={'|'.join(TRANSPORTS)}] [--host=...] [--port=...]")
        sys.exit(1)

    if transport == "sse":
        configure(host=host, port=port)

    get_mcp().run(transport=transport)


if __name__ == "__main__":
    main()