# Qcode Web API Documentation

## Overview

Qcode Web API provides HTTP/WebSocket endpoints for the Qcode Web UI frontend.

## Base URL

```
http://127.0.0.1:8000
```

## Authentication

Currently, no authentication is required. (This may change in production.)

---

## HTTP API Endpoints

### Health Check

**GET** `/api/health`

Check if the API server is running.

**Response:**

```json
{
  "status": "ok",
  "service": "qcode-web-api"
}
```

---

### Get Team Status

**GET** `/api/team`

Get current team status including lead name and all teammates.

**Response:**

```json
{
  "lead_name": "ld",
  "teammates": [
    {
      "name": "backend",
      "role": "backend",
      "status": "idle",
      "last_active": "2024-01-01T00:00:00Z"
    },
    {
      "name": "frontend",
      "role": "frontend",
      "status": "idle",
      "last_active": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### Get Task Graph

**GET** `/api/tasks`

Get the current task graph categorized by status.

**Response:**

```json
{
  "ready": [
    {
      "id": 1,
      "subject": "Implement feature X",
      "owner": "backend",
      "requiredRole": "backend",
      "status": "pending",
      "blockedBy": []
    }
  ],
  "in_progress": [],
  "blocked": [],
  "completed": []
}
```

---

### Chat (SSE Stream)

**POST** `/api/chat`

Send a message and receive streaming responses via Server-Sent Events (SSE).

**Request Body:**

```json
{
  "message": "Hello, how can you help me?",
  "role": "user"
}
```

**Response (SSE Stream):**

Events are sent as `data:` lines. Each line contains a JSON object with a `type` field.

**Event Types:**

- `token` - A text token from the AI response
- `tool_call` - Tool function being called
- `tool_output` - Tool output result
- `done` - Stream complete
- `error` - Error occurred

**Example Stream:**

```
data: {"type": "token", "content": "Hello"}

data: {"type": "token", "content": "!"}

data: {"type": "done"}
```

---

### Approve Plan

**POST** `/api/plans/approve`

Approve or reject a plan approval request.

**Request Body:**

```json
{
  "request_id": "abc123",
  "approve": true,
  "reason": "Plan looks good, proceed."
}
```

**Response:**

```json
{
  "status": "ok",
  "record": {
    "request_id": "abc123",
    "kind": "plan_approval",
    "status": "approved",
    "response": {
      "responder": "ld",
      "approve": true,
      "content": "Plan looks good, proceed."
    }
  }
}
```

---

### Respond to Shutdown

**POST** `/api/shutdown/respond`

Approve or reject a shutdown request.

**Request Body:**

```json
{
  "request_id": "def456",
  "approve": false,
  "reason": "Not ready to shutdown yet."
}
```

**Response:**

```json
{
  "status": "ok",
  "record": {
    "request_id": "def456",
    "kind": "shutdown",
    "status": "rejected",
    "response": {
      "responder": "ld",
      "approve": false,
      "content": "Not ready to shutdown yet."
    }
  }
}
```

---

## WebSocket Endpoint

### Real-time Updates

**WebSocket** `/ws`

Connect to receive real-time updates about team, task, and protocol changes.

**Connection:**

```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

**Message Types:**

- `team_update` - Team member status changes
- `task_update` - Task status changes
- `protocol_update` - Protocol/approval updates
- `echo` - Echo of sent messages (for testing)

**Example Message:**

```json
{
  "type": "task_update",
  "event_type": "task.updated",
  "payload": {
    "task_id": 1,
    "status": "in_progress"
  }
}
```

---

## Server-Sent Events (SSE) Details

The `/api/chat` endpoint uses Server-Sent Events for streaming AI responses.

### SSE Event Format

Each event is a line starting with `data:` followed by a JSON object:

```
data: {"type": "...", ...}
```

### Event Types Reference

| Type | Description | Fields |
|------|-------------|--------|
| `token` | Text token from AI | `content` (string) |
| `tool_call` | Tool function being called | `function` (string), `arguments` (object) |
| `tool_output` | Tool result | `function` (string), `output` (string, truncated) |
| `done` | Stream complete | (no additional fields) |
| `error` | Error occurred | `message` (string) |

### Consuming SSE in JavaScript

```javascript
const response = await fetch('http://127.0.0.1:8000/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'Hello', role: 'user' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  const lines = text.split('\n').filter(line => line.startsWith('data:'));

  for (const line of lines) {
    const data = JSON.parse(line.slice(5));
    console.log('Event:', data);
  }
}
```

---

## Error Handling

All endpoints may return HTTP errors:

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid JSON or parameters |
| 404 | Not Found - Resource does not exist |
| 503 | Service Unavailable - Backend component not initialized |

Error Response Format:

```json
{
  "detail": "Error message description"
}
```

---

## CORS

The API allows cross-origin requests from any origin (`*`) for development. This will be restricted in production.

---

## Testing the API

### Using curl

```bash
# Health check
curl http://127.0.0.1:8000/api/health

# Get team status
curl http://127.0.0.1:8000/api/team

# Get tasks
curl http://127.0.0.1:8000/api/tasks

# Chat (SSE)
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "role": "user"}'

# Approve plan
curl -X POST http://127.0.0.1:8000/api/plans/approve \
  -H "Content-Type: application/json" \
  -d '{"request_id": "abc123", "approve": true}'
```

### Using Python

```python
import http requests

# Health check
response = requests.get('http://127.0.0.1:8000/api/health')
print(response.json())

# Get team status
team = requests.get('http://127.0.0.1:8000/api/team').json()
print(team)

# Chat (SSE)
import httpx
async with httpx.AsyncClient() as client:
    async with client.stream(
        'POST',
        'http://127.0.0.1:8000/api/chat',
        json={'message': 'Hello', 'role': 'user'}
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith('data:'):
                data = json.loads(line[5:])
                print(data)
```

---

## Development

### Running the Server

```bash
# Using the provided script
python -m qcode.api.server --host 127.0.0.1 --port 8000

# Or using uvicorn directly
uvicorn qcode.api.server:app --host 127.0.0.1 --port 8000 --reload
```

### Interactive API Docs

When the server is running, visit:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## Future Enhancements

- [ ] Authentication/Authorization
- [ ] Rate limiting
- [ ] WebSocket authentication
- [ ] Response caching
- [ ] Request validation improvements
- [ ] OpenAPI schema customization
- [ ] API versioning
