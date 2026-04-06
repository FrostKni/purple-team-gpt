# Purple Team GPT API Documentation

> Comprehensive REST and WebSocket API reference for the Purple Team GPT autonomous cybersecurity simulation framework.

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Common Patterns](#common-patterns)
- [Authentication Endpoints](#authentication-endpoints)
- [User Endpoints](#user-endpoints)
- [Session Endpoints](#session-endpoints)
- [Feedback Endpoints](#feedback-endpoints)
- [LLM Provider Endpoints](#llm-provider-endpoints)
- [Settings Endpoints](#settings-endpoints)
- [WebSocket Events](#websocket-events)
- [Error Responses](#error-responses)
- [Data Models](#data-models)

---

## Overview

Purple Team GPT provides a RESTful API for managing cybersecurity simulation sessions, along with WebSocket support for real-time updates. The API enables you to:

- Register and authenticate users
- Create and manage simulation sessions
- Control Red (offensive) and Blue (defensive) agents
- Submit and manage feedback on agent interactions
- Configure LLM providers and endpoints
- Monitor system status and metrics

**API Version**: v1  
**Content-Type**: `application/json`  
**Accept**: `application/json`

---

## Base URL

```
http://localhost:8000/api/v1
```

For production deployments, replace `localhost:8000` with your domain.

**Health Check**: `GET /health` (unauthenticated)  
**API Status**: `GET /status` (authenticated)

---

## Authentication

All endpoints (except registration, login, and health check) require JWT authentication.

### Obtaining a Token

1. **Register** a new account via `POST /api/v1/auth/register`
2. **Login** via `POST /api/v1/auth/login`
3. Include the token in subsequent requests

### Using the Token

Include the JWT token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

### Example

```bash
# Login to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "yourpassword"}'

# Use token in subsequent request
curl -X GET http://localhost:8000/api/v1/sessions/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token Expiration

Tokens expire based on the `JWT_EXPIRE_MINUTES` configuration (default: 60 minutes). When a token expires, you'll receive a `401 Unauthorized` response with the message "Token has expired".

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse.

### Default Limits

- **Requests**: 100 requests per minute per IP address
- **Window**: 60 seconds (sliding window)

### Rate Limit Headers

All responses include rate limit headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 45
```

### Rate Limit Exceeded

When rate limited, you'll receive a `429 Too Many Requests` response:

```json
{
  "detail": "Rate limit exceeded. Try again in 45 seconds."
}
```

---

## Common Patterns

### Pagination

List endpoints support pagination via query parameters:

```
GET /api/v1/users/?skip=0&limit=20
GET /api/v1/feedback/?page=1&page_size=20
```

### Filtering

Many list endpoints support filtering:

```
GET /api/v1/sessions/?status=running
GET /api/v1/feedback/?agent_type=red&min_rating=4
```

### Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Error message describing the issue"
}
```

---

## Authentication Endpoints

Base path: `/api/v1/auth`

### Register User

Create a new user account.

**Endpoint**: `POST /api/v1/auth/register`  
**Authentication**: None  
**Rate Limited**: Yes

#### Request

```json
{
  "email": "analyst@company.com",
  "password": "SecurePassword123!",
  "full_name": "Security Analyst"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | Valid email address |
| `password` | string | Yes | 8-128 characters |
| `full_name` | string | No | User's full name |

#### Response (201 Created)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "analyst@company.com",
    "full_name": "Security Analyst",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 400 | Email already registered |
| 422 | Validation error (invalid email, password too short) |

---

### Login

Authenticate and receive a JWT token.

**Endpoint**: `POST /api/v1/auth/login`  
**Authentication**: None  
**Rate Limited**: Yes

#### Request

```json
{
  "email": "analyst@company.com",
  "password": "SecurePassword123!"
}
```

#### Response (200 OK)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "analyst@company.com",
    "full_name": "Security Analyst",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 401 | Invalid email or password |
| 401 | User account is disabled |

---

### Get Current User

Retrieve the authenticated user's profile.

**Endpoint**: `GET /api/v1/auth/me`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <token>"
```

#### Response (200 OK)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "analyst@company.com",
  "full_name": "Security Analyst",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 401 | Not authenticated |
| 401 | Invalid token payload |

---

## User Endpoints

Base path: `/api/v1/users`

### List Users

Retrieve a paginated list of users.

**Endpoint**: `GET /api/v1/users/`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```bash
curl -X GET "http://localhost:8000/api/v1/users/?skip=0&limit=100" \
  -H "Authorization: Bearer <token>"
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Number of records to skip |
| `limit` | integer | 100 | Maximum records to return |

#### Response (200 OK)

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "analyst@company.com",
    "full_name": "Security Analyst",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "email": "admin@company.com",
    "full_name": "System Admin",
    "is_active": true,
    "is_verified": true,
    "created_at": "2024-01-10T08:00:00Z"
  }
]
```

---

### Get User by ID

Retrieve a specific user by their ID.

**Endpoint**: `GET /api/v1/users/{user_id}`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string (UUID) | User's unique identifier |

#### Request

```bash
curl -X GET http://localhost:8000/api/v1/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <token>"
```

#### Response (200 OK)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "analyst@company.com",
  "full_name": "Security Analyst",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 404 | User not found |

---

## Session Endpoints

Base path: `/api/v1/sessions`

### Create Session

Create a new simulation session with Red and Blue agents.

**Endpoint**: `POST /api/v1/sessions/`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```json
{
  "target": "192.168.1.0/24",
  "scope": "Authorized penetration test for ACME Corp. Scope includes web applications and internal network. Exclude production databases.",
  "metadata": {
    "project_id": "PT-2024-001",
    "client": "ACME Corp",
    "authorized_by": "John Smith, CISO"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | string | Yes | Target specification (IP, CIDR, hostname, or URL) |
| `scope` | string | No | Scope restrictions and constraints (max 2000 chars) |
| `metadata` | object | No | Additional session metadata |

**Security Note**: The target field is validated to prevent command injection. Dangerous characters (`;`, `|`, `` ` ``, `$()`, `&`, `>`, `<`, newlines) are blocked.

#### Response (201 Created)

```json
{
  "id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "target": "192.168.1.0/24",
  "scope": "Authorized penetration test for ACME Corp...",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "started_at": null,
  "completed_at": null
}
```

---

### List Sessions

Retrieve all sessions with optional status filtering.

**Endpoint**: `GET /api/v1/sessions/`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```bash
curl -X GET "http://localhost:8000/api/v1/sessions/?status=running" \
  -H "Authorization: Bearer <token>"
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status: `pending`, `running`, `paused`, `completed`, `error` |

#### Response (200 OK)

```json
{
  "sessions": [
    {
      "id": "sess_550e8400-e29b-41d4-a716-446655440000",
      "target": "192.168.1.0/24",
      "scope": "Authorized penetration test...",
      "status": "running",
      "created_at": "2024-01-15T10:30:00Z",
      "started_at": "2024-01-15T10:31:00Z",
      "completed_at": null
    }
  ],
  "total": 1
}
```

---

### Get Session

Retrieve detailed information about a specific session.

**Endpoint**: `GET /api/v1/sessions/{session_id}`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```bash
curl -X GET http://localhost:8000/api/v1/sessions/sess_550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <token>"
```

#### Response (200 OK)

```json
{
  "id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "target": "192.168.1.0/24",
  "scope": "Authorized penetration test...",
  "status": "running",
  "created_at": "2024-01-15T10:30:00Z",
  "started_at": "2024-01-15T10:31:00Z",
  "completed_at": null
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 404 | Session not found |

---

### Start Session

Start a pending or paused simulation session.

**Endpoint**: `POST /api/v1/sessions/{session_id}/start`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```bash
curl -X POST http://localhost:8000/api/v1/sessions/sess_550e8400-e29b-41d4-a716-446655440000/start \
  -H "Authorization: Bearer <token>"
```

#### Response (200 OK)

```json
{
  "message": "Session started",
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "status": "running"
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 404 | Session not found |
| 400 | Session already running |
| 400 | Cannot restart a completed session |

---

### Pause Session

Pause a running session. Can be resumed later.

**Endpoint**: `POST /api/v1/sessions/{session_id}/pause`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```bash
curl -X POST http://localhost:8000/api/v1/sessions/sess_550e8400-e29b-41d4-a716-446655440000/pause \
  -H "Authorization: Bearer <token>"
```

#### Response (200 OK)

```json
{
  "message": "Session paused",
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "status": "paused"
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 404 | Session not found |
| 400 | Cannot pause session - not running |

---

### Resume Session

Resume a paused session.

**Endpoint**: `POST /api/v1/sessions/{session_id}/resume`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```bash
curl -X POST http://localhost:8000/api/v1/sessions/sess_550e8400-e29b-41d4-a716-446655440000/resume \
  -H "Authorization: Bearer <token>"
```

#### Response (200 OK)

```json
{
  "message": "Session resumed",
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "status": "running"
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 404 | Session not found |
| 400 | Cannot resume session - not paused |

---

### Stop Session

Stop a session permanently. Cannot be resumed.

**Endpoint**: `POST /api/v1/sessions/{session_id}/stop`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```bash
curl -X POST http://localhost:8000/api/v1/sessions/sess_550e8400-e29b-41d4-a716-446655440000/stop \
  -H "Authorization: Bearer <token>"
```

#### Response (200 OK)

```json
{
  "message": "Session stopped",
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "status": "completed"
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 404 | Session not found |

---

### Get Session Metrics

Retrieve detailed metrics for a session.

**Endpoint**: `GET /api/v1/sessions/{session_id}/metrics`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```bash
curl -X GET http://localhost:8000/api/v1/sessions/sess_550e8400-e29b-41d4-a716-446655440000/metrics \
  -H "Authorization: Bearer <token>"
```

#### Response (200 OK)

```json
{
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "target": "192.168.1.0/24",
  "scope": "Authorized penetration test...",
  "status": "completed",
  "duration": "00:45:23",
  "red_agent": {
    "steps_completed": 47,
    "findings": 12,
    "tools_used": ["nmap", "nikto", "sqlmap"]
  },
  "blue_agent": {
    "steps_completed": 43,
    "detections": 8,
    "tools_used": ["log_monitor", "firewall_manager"]
  },
  "total_findings": 20,
  "total_events": 156
}
```

---

### Get Session Findings

Retrieve all findings from Red and Blue agents.

**Endpoint**: `GET /api/v1/sessions/{session_id}/findings/`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```bash
curl -X GET http://localhost:8000/api/v1/sessions/sess_550e8400-e29b-41d4-a716-446655440000/findings/ \
  -H "Authorization: Bearer <token>"
```

#### Response (200 OK)

```json
{
  "red_findings": [
    {
      "id": "finding_001",
      "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
      "agent": "red",
      "title": "SQL Injection in Login Form",
      "severity": "critical",
      "description": "SQL injection vulnerability found in /login endpoint",
      "evidence": "Payload: ' OR '1'='1' --",
      "recommendation": "Implement parameterized queries",
      "cve": null,
      "cvss_score": 9.8,
      "category": "injection",
      "tool": "sqlmap",
      "timestamp": "2024-01-15T10:45:00Z"
    }
  ],
  "blue_detections": [
    {
      "id": "detection_001",
      "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
      "agent": "blue",
      "title": "Suspicious SQL Pattern Detected",
      "severity": "high",
      "description": "SQL injection pattern detected in application logs",
      "evidence": "Pattern matched: ' OR '1'='1",
      "recommendation": "Block source IP and investigate",
      "timestamp": "2024-01-15T10:45:05Z"
    }
  ]
}
```

---

### Delete Session

Delete a session and all associated data.

**Endpoint**: `DELETE /api/v1/sessions/{session_id}`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Request

```bash
curl -X DELETE http://localhost:8000/api/v1/sessions/sess_550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <token>"
```

#### Response (200 OK)

```json
{
  "message": "Session deleted",
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000"
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 404 | Session not found |

---

## Feedback Endpoints

Base path: `/api/v1/feedback`

The feedback system allows rating agent interactions (1-5 stars) and exporting high-quality interactions for fine-tuning.

### Submit Feedback

Submit feedback for an agent interaction.

**Endpoint**: `POST /api/v1/feedback/`  
**Authentication**: Not required (can include user_id)  
**Rate Limited**: Yes

#### Request

```json
{
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "interaction_id": "interaction_001",
  "agent_type": "red",
  "prompt": "What vulnerabilities exist in the target network?",
  "response": "Based on the nmap scan, I identified 3 open ports...",
  "rating": 5,
  "comment": "Excellent analysis with actionable findings",
  "user_id": "analyst_001",
  "context": "{\"target\": \"192.168.1.0/24\", \"scan_type\": \"full\"}"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | Yes | Session identifier |
| `interaction_id` | string | Yes | Unique interaction identifier |
| `agent_type` | string | Yes | `red`, `blue`, or `orchestrator` |
| `prompt` | string | Yes | The input prompt/question |
| `response` | string | Yes | The agent's response |
| `rating` | integer | Yes | Rating from 1-5 |
| `comment` | string | No | Optional comment |
| `user_id` | string | No | Optional user identifier |
| `context` | string | No | Additional context (JSON) |

#### Response (201 Created)

```json
{
  "id": 1,
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "interaction_id": "interaction_001",
  "agent_type": "red",
  "prompt": "What vulnerabilities exist in the target network?",
  "response": "Based on the nmap scan, I identified 3 open ports...",
  "rating": 5,
  "comment": "Excellent analysis with actionable findings",
  "created_at": "2024-01-15T11:00:00Z",
  "user_id": "analyst_001"
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 409 | Feedback already exists for this interaction |
| 422 | Validation error (rating out of range, etc.) |

---

### List Feedback

Retrieve paginated feedback entries with filters.

**Endpoint**: `GET /api/v1/feedback/`  
**Authentication**: Not required  
**Rate Limited**: Yes

#### Request

```bash
curl -X GET "http://localhost:8000/api/v1/feedback/?agent_type=red&min_rating=4&page=1&page_size=20" \
  -H "Authorization: Bearer <token>"
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | Filter by session |
| `agent_type` | string | Filter by agent: `red`, `blue`, `orchestrator` |
| `min_rating` | integer | Minimum rating (1-5) |
| `max_rating` | integer | Maximum rating (1-5) |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Items per page (default: 20, max: 100) |

#### Response (200 OK)

```json
{
  "feedback": [
    {
      "id": 1,
      "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
      "interaction_id": "interaction_001",
      "agent_type": "red",
      "prompt": "What vulnerabilities exist?",
      "response": "Based on the nmap scan...",
      "rating": 5,
      "comment": "Excellent analysis",
      "created_at": "2024-01-15T11:00:00Z",
      "user_id": "analyst_001"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

### Get Feedback Statistics

Retrieve aggregate feedback statistics.

**Endpoint**: `GET /api/v1/feedback/stats`  
**Authentication**: Not required  
**Rate Limited**: Yes

#### Response (200 OK)

```json
{
  "total_feedback": 150,
  "average_rating": 4.2,
  "rating_distribution": {
    "1": 5,
    "2": 10,
    "3": 25,
    "4": 50,
    "5": 60
  },
  "by_agent_type": {
    "red": 80,
    "blue": 60,
    "orchestrator": 10
  },
  "high_rated_count": 110
}
```

---

### Get Feedback by ID

Retrieve a specific feedback entry.

**Endpoint**: `GET /api/v1/feedback/{feedback_id}`  
**Authentication**: Not required  
**Rate Limited**: Yes

#### Response (200 OK)

```json
{
  "id": 1,
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "interaction_id": "interaction_001",
  "agent_type": "red",
  "prompt": "What vulnerabilities exist?",
  "response": "Based on the nmap scan...",
  "rating": 5,
  "comment": "Excellent analysis",
  "created_at": "2024-01-15T11:00:00Z",
  "user_id": "analyst_001"
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 404 | Feedback not found |

---

### Update Feedback

Update rating or comment for existing feedback.

**Endpoint**: `PUT /api/v1/feedback/{feedback_id}`  
**Authentication**: Not required  
**Rate Limited**: Yes

#### Request

```json
{
  "rating": 4,
  "comment": "Good analysis, but could be more detailed"
}
```

#### Response (200 OK)

```json
{
  "id": 1,
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "interaction_id": "interaction_001",
  "agent_type": "red",
  "prompt": "What vulnerabilities exist?",
  "response": "Based on the nmap scan...",
  "rating": 4,
  "comment": "Good analysis, but could be more detailed",
  "created_at": "2024-01-15T11:00:00Z",
  "user_id": "analyst_001"
}
```

---

### Delete Feedback

Delete a feedback entry.

**Endpoint**: `DELETE /api/v1/feedback/{feedback_id}`  
**Authentication**: Not required  
**Rate Limited**: Yes

#### Response (200 OK)

```json
{
  "message": "Feedback deleted",
  "id": 1
}
```

---

### Export Feedback for Fine-tuning

Export high-rated feedback to JSONL format for LLM fine-tuning.

**Endpoint**: `POST /api/v1/feedback/export`  
**Authentication**: Not required  
**Rate Limited**: Yes

#### Request

```bash
curl -X POST "http://localhost:8000/api/v1/feedback/export?min_rating=4&agent_type=red" \
  -H "Authorization: Bearer <token>"
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_rating` | integer | 4 | Minimum rating threshold |
| `agent_type` | string | null | Filter by agent type |
| `session_id` | string | null | Filter by session |
| `output_path` | string | `./data/finetuning/feedback_export.jsonl` | Output file path |

#### Response (200 OK)

```json
{
  "success": true,
  "count": 45,
  "output_path": "./data/finetuning/feedback_export.jsonl",
  "message": "Exported 45 feedback entries"
}
```

---

### Delete Session Feedback

Delete all feedback for a specific session.

**Endpoint**: `DELETE /api/v1/feedback/session/{session_id}`  
**Authentication**: Not required  
**Rate Limited**: Yes

#### Response (200 OK)

```json
{
  "message": "Deleted all feedback for session",
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "count": 15
}
```

---

## LLM Provider Endpoints

Base path: `/api/v1/llm`

Manage LLM providers and OpenAI-compatible endpoints.

### List Providers

List all available LLM providers and their models.

**Endpoint**: `GET /api/v1/llm/providers`  
**Authentication**: Not required  
**Rate Limited**: No

#### Response (200 OK)

```json
[
  {
    "name": "openai",
    "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
  },
  {
    "name": "google",
    "models": ["gemini-pro", "gemini-1.5-pro"]
  },
  {
    "name": "openai_compatible:local-llm",
    "models": ["llama-2-70b", "mistral-7b"]
  }
]
```

---

### List Endpoints

List all configured OpenAI-compatible endpoints.

**Endpoint**: `GET /api/v1/llm/endpoints`  
**Authentication**: Not required  
**Rate Limited**: No

#### Response (200 OK)

```json
[
  {
    "name": "local-llm",
    "base_url": "http://localhost:8000/v1",
    "model": "llama-2-70b",
    "enabled": true,
    "timeout": 300
  },
  {
    "name": "openrouter",
    "base_url": "https://openrouter.ai/api/v1",
    "model": "anthropic/claude-2",
    "enabled": true,
    "timeout": 300
  }
]
```

---

### Add Endpoint

Add a new OpenAI-compatible endpoint.

**Endpoint**: `POST /api/v1/llm/endpoints`  
**Authentication**: Not required  
**Rate Limited**: Yes

#### Request

```json
{
  "name": "local-llm",
  "api_key": "not-needed",
  "base_url": "http://localhost:8000/v1",
  "model": "llama-2-70b",
  "enabled": true,
  "timeout": 300
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Friendly name for the endpoint |
| `api_key` | string | No | API key (can be any string for local servers) |
| `base_url` | string | Yes | Base URL for the OpenAI-compatible API |
| `model` | string | Yes | Default model to use |
| `enabled` | boolean | No | Whether endpoint is enabled (default: true) |
| `timeout` | integer | No | Request timeout in seconds (default: 300) |

#### Response (201 Created)

```json
{
  "name": "local-llm",
  "base_url": "http://localhost:8000/v1",
  "model": "llama-2-70b",
  "enabled": true,
  "timeout": 300
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 400 | Endpoint with this name already exists |
| 503 | LLM engine not initialized |

---

### Update Endpoint

Update an existing endpoint configuration.

**Endpoint**: `PATCH /api/v1/llm/endpoints/{name}`  
**Authentication**: Not required  
**Rate Limited**: Yes

#### Request

Same as Add Endpoint.

#### Response (200 OK)

Same as Add Endpoint.

#### Errors

| Status | Description |
|--------|-------------|
| 404 | Endpoint not found |
| 503 | LLM engine not initialized |

---

### Remove Endpoint

Remove an OpenAI-compatible endpoint.

**Endpoint**: `DELETE /api/v1/llm/endpoints/{name}`  
**Authentication**: Not required  
**Rate Limited**: Yes

#### Response (200 OK)

```json
{
  "message": "Endpoint 'local-llm' removed"
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 404 | Endpoint not found |

---

### Test Connection

Test connection to an LLM provider.

**Endpoint**: `POST /api/v1/llm/test`  
**Authentication**: Not required  
**Rate Limited**: Yes

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `provider` | string | Provider name (optional) |
| `model` | string | Model to test (optional) |

#### Response (200 OK)

```json
{
  "success": true,
  "provider": "openai",
  "model": "gpt-4",
  "response_preview": "OK"
}
```

#### Response (200 OK - Failed)

```json
{
  "success": false,
  "provider": "openai",
  "model": "gpt-4",
  "error": "API key invalid"
}
```

---

## Settings Endpoints

Base path: `/api/v1/settings`

### Get Settings

Retrieve current application settings.

**Endpoint**: `GET /api/v1/settings/`  
**Authentication**: Required  
**Rate Limited**: Yes

#### Response (200 OK)

```json
{
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  "llm_failover": "enabled",
  "vector_db": "ChromaDB",
  "vector_db_status": "healthy",
  "message_queue": "Redis",
  "message_queue_status": "healthy",
  "management_network": "purple-team-network",
  "attack_network": "attack-network",
  "safe_mode": true,
  "max_concurrent_tasks": 5
}
```

---

## WebSocket Events

WebSocket support provides real-time updates for session activities.

### Connection

**General WebSocket**: `ws://localhost:8000/ws?token=<jwt_token>`  
**Session WebSocket**: `ws://localhost:8000/ws/session/<session_id>?token=<jwt_token>`

### Authentication

Pass the JWT token as a query parameter:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/session/sess_123?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...');
```

### Connection Messages

#### Connected (Server → Client)

```json
{
  "type": "connected",
  "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
  "message": "Connected to session sess_550e8400-e29b-41d4-a716-446655440000",
  "user": "analyst@company.com"
}
```

#### Session State (Server → Client)

Sent immediately after connection:

```json
{
  "type": "session_state",
  "session": {
    "id": "sess_550e8400-e29b-41d4-a716-446655440000",
    "target": "192.168.1.0/24",
    "status": "running",
    "red_findings_count": 5,
    "blue_findings_count": 3,
    "total_events": 42
  }
}
```

---

### Event Types

#### Agent Event (Server → Client)

Emitted when an agent performs an action:

```json
{
  "type": "event",
  "agent": "red",
  "event_type": "step",
  "data": {
    "step_number": 15,
    "action": "scan",
    "tool": "nmap",
    "target": "192.168.1.1",
    "result": "Found open ports: 22, 80, 443"
  },
  "timestamp": "2024-01-15T10:45:00Z"
}
```

#### Finding Event (Server → Client)

Emitted when a finding is discovered:

```json
{
  "type": "event",
  "agent": "red",
  "event_type": "finding",
  "data": {
    "id": "finding_015",
    "title": "Open SSH Port with Weak Configuration",
    "severity": "medium",
    "description": "SSH port 22 is open with password authentication enabled",
    "recommendation": "Disable password authentication and use key-based auth"
  },
  "timestamp": "2024-01-15T10:46:00Z"
}
```

#### Error Event (Server → Client)

Emitted when an error occurs:

```json
{
  "type": "event",
  "agent": "red",
  "event_type": "error",
  "data": {
    "error": "Tool execution failed",
    "tool": "nikto",
    "message": "Connection timeout to target"
  },
  "timestamp": "2024-01-15T10:47:00Z"
}
```

---

### Client Messages

#### Ping (Client → Server)

```json
{
  "type": "ping"
}
```

Server responds with:

```json
{
  "type": "pong"
}
```

#### Pause Command (Client → Server)

```json
{
  "type": "command",
  "command": "pause"
}
```

Response:

```json
{
  "type": "command_result",
  "command": "pause",
  "success": true,
  "message": "Session paused"
}
```

#### Resume Command (Client → Server)

```json
{
  "type": "command",
  "command": "resume"
}
```

#### Stop Command (Client → Server)

```json
{
  "type": "command",
  "command": "stop"
}
```

#### Get Metrics (Client → Server)

```json
{
  "type": "get_metrics"
}
```

Response:

```json
{
  "type": "metrics",
  "data": {
    "session_id": "sess_550e8400-e29b-41d4-a716-446655440000",
    "status": "running",
    "duration": "00:15:30",
    "red_agent": { "steps": 20, "findings": 5 },
    "blue_agent": { "steps": 18, "detections": 3 }
  }
}
```

#### Submit Feedback (Client → Server)

```json
{
  "type": "feedback",
  "feedback_type": "rating",
  "content": "Good analysis of the target network",
  "rating": 4,
  "metadata": {
    "step_number": 15,
    "agent": "red"
  }
}
```

Response:

```json
{
  "type": "feedback_stored",
  "doc_id": "doc_550e8400-e29b-41d4-a716-446655440000",
  "message": "Feedback stored successfully"
}
```

---

### WebSocket Status Endpoint

Check WebSocket connection status.

**Endpoint**: `GET /ws/status`  
**Authentication**: Not required

#### Response (200 OK)

```json
{
  "active_sessions": ["sess_550e8400-e29b-41d4-a716-446655440000"],
  "connections_per_session": {
    "sess_550e8400-e29b-41d4-a716-446655440000": 3
  }
}
```

---

## Error Responses

All error responses follow a consistent format.

### Error Format

```json
{
  "detail": "Human-readable error message"
}
```

### Common HTTP Status Codes

| Status | Description |
|--------|-------------|
| 400 | Bad Request - Invalid input or validation error |
| 401 | Unauthorized - Missing or invalid authentication |
| 403 | Forbidden - Authenticated but not authorized |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server-side error |
| 503 | Service Unavailable - Component not initialized |

### Validation Errors (422)

```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must be at least 8 characters",
      "type": "value_error"
    }
  ]
}
```

### Authentication Errors (401)

```json
{
  "detail": "Token has expired",
  "headers": {
    "WWW-Authenticate": "Bearer"
  }
}
```

```json
{
  "detail": "Not authenticated",
  "headers": {
    "WWW-Authenticate": "Bearer"
  }
}
```

### Rate Limit Errors (429)

```json
{
  "detail": "Rate limit exceeded. Try again in 45 seconds."
}
```

Headers include:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 45
```

---

## Data Models

### Session Status

| Status | Description |
|--------|-------------|
| `pending` | Session created, not started |
| `initializing` | Agents being initialized |
| `running` | Session actively running |
| `paused` | Session paused by user |
| `completed` | Session finished normally |
| `error` | Session terminated due to error |
| `cleaning_up` | Session cleanup in progress |

### Agent Types

| Type | Description |
|------|-------------|
| `red` | Offensive security agent |
| `blue` | Defensive security agent |
| `orchestrator` | Coordination agent |

### Finding Severity

| Severity | Description |
|----------|-------------|
| `critical` | Immediate action required |
| `high` | Significant security impact |
| `medium` | Moderate security impact |
| `low` | Minor security impact |
| `info` | Informational finding |

---

## Example Workflows

### Complete Session Workflow

```bash
# 1. Register or Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "analyst@company.com", "password": "password"}' | jq -r '.access_token')

# 2. Create a session
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/v1/sessions/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target": "192.168.1.0/24", "scope": "Authorized pentest"}' | jq -r '.id')

# 3. Connect to WebSocket for real-time updates
# (In browser or WebSocket client)
# ws://localhost:8000/ws/session/$SESSION_ID?token=$TOKEN

# 4. Start the session
curl -X POST http://localhost:8000/api/v1/sessions/$SESSION_ID/start \
  -H "Authorization: Bearer $TOKEN"

# 5. Monitor via WebSocket or poll metrics
curl -X GET http://localhost:8000/api/v1/sessions/$SESSION_ID/metrics \
  -H "Authorization: Bearer $TOKEN"

# 6. Pause if needed
curl -X POST http://localhost:8000/api/v1/sessions/$SESSION_ID/pause \
  -H "Authorization: Bearer $TOKEN"

# 7. Stop when done
curl -X POST http://localhost:8000/api/v1/sessions/$SESSION_ID/stop \
  -H "Authorization: Bearer $TOKEN"

# 8. Get final report
curl -X GET http://localhost:8000/api/v1/sessions/$SESSION_ID/findings/ \
  -H "Authorization: Bearer $TOKEN"
```

### JavaScript WebSocket Example

```javascript
const token = 'your_jwt_token';
const sessionId = 'sess_550e8400-e29b-41d4-a716-446655440000';

const ws = new WebSocket(`ws://localhost:8000/ws/session/${sessionId}?token=${token}`);

ws.onopen = () => {
  console.log('Connected to session');
  
  // Keep-alive ping
  setInterval(() => {
    ws.send(JSON.stringify({ type: 'ping' }));
  }, 30000);
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'connected':
      console.log('Connection confirmed:', data.message);
      break;
    case 'session_state':
      console.log('Session state:', data.session);
      break;
    case 'event':
      if (data.event_type === 'finding') {
        console.log('New finding:', data.data);
      } else if (data.event_type === 'step') {
        console.log('Agent step:', data.agent, data.data);
      }
      break;
    case 'pong':
      // Ping response
      break;
  }
};

// Pause session
ws.send(JSON.stringify({ type: 'command', command: 'pause' }));

// Submit feedback
ws.send(JSON.stringify({
  type: 'feedback',
  feedback_type: 'rating',
  content: 'Good analysis',
  rating: 4
}));

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
};
```

---

## OpenAPI Documentation

Interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## Versioning

The API is versioned via the URL path (`/api/v1/`). Breaking changes will be introduced in new versions (`/api/v2/`, etc.) while maintaining backward compatibility for existing versions.

Current version: **v1**

---

## Support

For issues and feature requests, please visit the project repository or contact the development team.

**Last Updated**: 2024-01-15  
**API Version**: 1.0.0
