from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings


_mcp: FastMCP | None = None


def init(allowed_hosts: list[str] | None = None) -> None:
    """Create the shared FastMCP instance with the correct transport security.

    Must be called before importing any tool module, since tools decorate
    themselves on the instance at import time.

    Args:
        allowed_hosts: Hosts to whitelist in DNS rebinding protection.
                       Format: ["192.168.1.24:*", "192.168.1.0:*"].
                       None disables the protection entirely (stdio-safe).
    """
    global _mcp

    if allowed_hosts is not None:
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=[f"http://{h}" for h in allowed_hosts],
        )
    else:
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )

    _mcp = FastMCP("ProjectNavigator", transport_security=security)


def get_mcp() -> FastMCP:
    """Return the shared FastMCP instance.

    Raises:
        RuntimeError: If init() has not been called yet.
    """
    if _mcp is None:
        raise RuntimeError("FastMCP instance not initialized. Call init() first.")
    return _mcp