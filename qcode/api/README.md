# Qcode Web API Module

This module provides the FastAPI backend for Qcode Web UI.

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn[standard] pydantic starlette

# Run the server
uvicorn qcode.api.server:app --host 127.0.0.1 --port 8000

# Or use the provided script
python scripts/run_api_server.py
```

## Module Structure

```
qcode/api/
├── __init__.py       # Package exports
└── server.py         # FastAPI application factory and routes
```

## Key Components

### `get_app(workdir=None, profile=None)`

Creates and configures the FastAPI application with all Qcode runtime components.

### `run_server(host, port, workdir, profile)`

Convenience function to run the development server.

## Integration

The API integrates with existing Qcode runtime components:

- `TaskGraphManager` - for task management
- `TeammateManager` - for team coordination
- `TeamProtocolManager` - for approval workflows
- `AgentEngine` - for chat/AI responses
- `MessageBus` - for team messaging
- `EventSink` - for real-time WebSocket updates

## Testing

```python
from qcode.api import app

# Use FastAPI test client
from fastapi.testclient import TestClient
client = TestClient(app)

# Test endpoints
response = client.get('/api/health')
assert response.json()['status'] == 'ok'
```

## See Also

- [API Documentation](../../docs/API.md) - Full API reference
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
