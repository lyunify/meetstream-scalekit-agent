"""Connect MCP servers attached to the agent before starting a Realtime session."""

from __future__ import annotations

import logging

logger = logging.getLogger("bridge.realtime.mcp")


async def preconnect_mcp_servers(agent) -> None:
    """
    Connect each MCP server before Realtime starts. Servers that fail to connect
    are dropped from ``agent.mcp_servers`` so ``list_tools`` is not called on a
    disconnected client (SDK raises ``UserError: Server not initialized``).

    We always rebuild the server list from config so the singleton RealtimeAgent
    does not keep an empty ``mcp_servers`` after a failed connect on an earlier
    session.
    """
    from app.agent import build_mcp_servers

    mcp_servers = build_mcp_servers()
    try:
        agent.mcp_servers = mcp_servers
    except Exception:
        setattr(agent, "mcp_servers", mcp_servers)

    connected: list = []
    for srv in mcp_servers:
        try:
            if hasattr(srv, "connect"):
                is_connected = getattr(srv, "is_connected", False)
                if not is_connected:
                    await srv.connect()
            connected.append(srv)
        except Exception as e:
            logger.error(
                "MCP connect failed for %s: %s",
                getattr(srv, "name", "<unnamed>"),
                e,
            )
    try:
        agent.mcp_servers = connected
    except Exception:
        setattr(agent, "mcp_servers", connected)
    if not connected and mcp_servers:
        logger.warning(
            "All %d MCP server(s) failed to connect; Realtime session runs with local tools only.",
            len(mcp_servers),
        )
