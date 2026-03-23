# iCloud Calendar MCP Server

A local [MCP](https://modelcontextprotocol.io/) server for interacting with Apple Calendar via CalDAV, built with [FastMCP](https://github.com/jlowin/fastmcp).

## Setup

1. Clone the repo and create a virtual environment:

```bash
git clone https://github.com/bufordeeds/icloud-calendar-mcp.git
cd icloud-calendar-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

You need an **app-specific password** from [appleid.apple.com](https://appleid.apple.com/) under Sign-In and Security > App-Specific Passwords.

3. Add to Claude Code (user scope so it's available everywhere):

```bash
claude mcp add -s user --transport stdio icloud-calendar -- /path/to/icloud-calendar-mcp/.venv/bin/python /path/to/icloud-calendar-mcp/server.py
```

Or add to Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "icloud-calendar": {
      "command": "/path/to/icloud-calendar-mcp/.venv/bin/python",
      "args": ["/path/to/icloud-calendar-mcp/server.py"]
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `list_calendars` | List all calendars with name, URL, and color |
| `list_events` | List events from a calendar within a date range |
| `get_event` | Get full details of a specific event by UID |
| `create_event` | Create a new event |
| `update_event` | Update an existing event by UID |
| `delete_event` | Delete an event by UID |
| `search_events` | Search events across all calendars by text query |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ICLOUD_EMAIL` | Your iCloud email address |
| `ICLOUD_APP_PASSWORD` | App-specific password from Apple ID settings |
