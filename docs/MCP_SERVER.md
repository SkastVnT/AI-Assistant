# MCP Server

The MCP service uses FastMCP over stdio. It is not an HTTP listener.

| Item | Value |
|---|---|
| Entry point | `services/mcp-server/server.py` |
| Transport | stdio |
| Chatbot proxy routes | `services/chatbot/routes/mcp.py` |
| Requirements | `services/mcp-server/requirements.txt` and core profile dependencies |

Typical tools include file search, file reading, directory listing, project info, log search, and safe calculation helpers. When adding MCP tools, update the server implementation, chatbot proxy docs, and route/response tests.
