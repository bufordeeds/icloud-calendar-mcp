# iCloud Calendar MCP Server

A local MCP server that connects to Apple Calendar via CalDAV (iCloud).

## Setup

1. Generate an app-specific password at [appleid.apple.com](https://appleid.apple.com) under Sign-In and Security > App-Specific Passwords.

2. Create your `.env` file:
   ```bash
   cp .env.example .env
   ```
   Fill in your Apple ID email and app-specific password.

3. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Run the server:
   ```bash
   source .venv/bin/activate
   python server.py
   ```

## Claude Desktop Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "icloud-calendar": {
      "command": "/Users/buford/dev/tools/icloud-calendar-mcp/.venv/bin/python",
      "args": ["/Users/buford/dev/tools/icloud-calendar-mcp/server.py"]
    }
  }
}
```

## Tools

- **list_calendars** — list all calendars
- **list_events** — list events from a calendar within a date range
- **get_event** — get full details of a specific event by UID
- **create_event** — create a new event
- **update_event** — update an existing event by UID
- **delete_event** — delete an event by UID
- **search_events** — search events across all calendars by text query
