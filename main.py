import sys
import logging

TRANSPORTS = ("stdio", "sse")

# --- Initialisation globale pour mcp dev/run ---
# Ces imports déclenchent init() + enregistrement des outils
from app.mcp import init
init(allowed_hosts=None)

import app.tools   # noqa: F401
import app.prompts  # noqa: F401
import app.resources  # noqa: F401

from app.mcp import get_mcp
mcp = get_mcp()  # objet global visible par `mcp dev` et `mcp run`
# -----------------------------------------------


def main() -> None:
    transport = "stdio"
    host = "0.0.0.0"
    port = 8002
    allowed_hosts: list[str] | None = None

    for arg in sys.argv[1:]:
        if arg.startswith("--transport="):
            transport = arg.split("=", 1)[1]
        elif arg.startswith("--host="):
            host = arg.split("=", 1)[1]
        elif arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
        elif arg.startswith("--allowed-hosts="):
            allowed_hosts = arg.split("=", 1)[1].split(",")

    if transport not in TRANSPORTS:
        logging.warning(
            f"Usage: main.py [--transport={'|'.join(TRANSPORTS)}]"
            " [--host=...] [--port=...] [--allowed-hosts=host1,host2]"
        )
        sys.exit(1)

    if transport == "sse":
        # Re-init avec allowed_hosts pour SSE
        init(allowed_hosts=allowed_hosts)
        mcp.settings.host = host
        mcp.settings.port = port

    mcp.run(transport=transport)


if __name__ == "__main__":
    main()