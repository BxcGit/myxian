# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Xianyu (闲鱼) Auto-Reply Management System** with Vue 3 frontend and FastAPI backend. It connects to Xianyu servers via WebSocket to receive and handle customer messages automatically.

## Development Commands

### Frontend (Vue 3 + Vite)

```bash
cd frontend
pnpm install        # Install dependencies (uses pnpm)
pnpm dev           # Start dev server (http://localhost:5173)
pnpm build         # Production build
pnpm preview       # Preview production build
```

### Backend (FastAPI + Python)

```bash
cd backend
pip install -r requirements.txt   # Install dependencies
python run.py   # Start dev server (http://localhost:8000)
```

The backend runs on port 8000 and the frontend proxies to it.

## Architecture

```
myxianyu/
├── frontend/                    # Vue 3 SPA
│   ├── src/
│   │   ├── api.js              # Axios API calls (xianyuAccountApi, productApi, sessionApi)
│   │   ├── views/              # Page components
│   │   ├── components/         # Reusable components (ChatPanel, SessionList, etc.)
│   │   └── router/             # Vue Router config (routes.js)
│   └── vite.config.js
└── backend/
    └── app/
        ├── main.py             # FastAPI entry, CORS, router registration
        ├── config.py            # XianyuConfig (heartbeat, token refresh intervals)
        ├── database.py          # SQLite connection & init (users, xianyu_accounts, products, sessions, messages)
        ├── routers/             # API route handlers (all require JWT auth except /auth/login and /auth/register)
        │   ├── auth.py         # /auth/register, /auth/login, /auth/settings
        │   ├── xianyu_account.py # /xianyu-accounts/* (CRUD + start/stop)
        │   ├── product.py       # /products/* (CRUD + sync)
        │   └── session.py       # /sessions/* (CRUD + messages)
        ├── models/              # Pydantic request/response models
        │   ├── user.py, xianyu_account.py, product.py, session.py, message.py
        ├── utils/               # Utilities
        │   ├── security.py      # JWT, password hashing (bcrypt), password validation
        │   ├── auth.py          # Authentication dependency (get_current_user)
        │   ├── logger.py        # Structured logging with request tracking
        │   └── middleware.py    # Request logging middleware
        └── xianyu/              # Xianyu WebSocket core module
            ├── ws_client.py     # WebSocket client (connect to wss://wss-goofish.dingtalk.com/)
            ├── xianyu_api.py    # Xianyu API (token, item info)
            ├── handler_message.py # Message parsing & handling
            ├── account_context.py # Global account context manager (singleton)
            ├── manual_manager.py # Manual takeover mode manager (singleton)
            ├── token_manager.py  # Token refresh manager
            ├── heart_beat.py    # Heartbeat maintenance
            └── parser.py        # Message decryption & parsing
    ├── run.py                  # uvicorn entry point
    └── users.db                # SQLite database (auto-created)
```

## Authentication

The system uses **JWT (JSON Web Token)** for authentication.

### Auth Endpoints

- `POST /auth/register` - Register new user (body: `{username, password}`)
  - Password must be 8+ characters with letters and numbers
- `POST /auth/login` - Login (body: `{username, password}`)
  - Returns: `{access_token, token_type: "bearer", user_id, username}`

### Using Authenticated APIs

Include the JWT token in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

All other API endpoints (`/xianyu-accounts/*`, `/products/*`, `/sessions/*`) require authentication.

### User Data Isolation

Each user can only access their own data:
- `xianyu_accounts` are scoped by `user_id`
- `products` are accessed through `xianyu_account_id` (which has `user_id`)
- `sessions` and `messages` are accessed through `xianyu_account_id`

## Logging System

The system uses a **structured logging** system with request tracking.

### Log Files

Logs are stored in `backend/logs/`:
- `app.log` - Application lifecycle events
- `auth.log` - Authentication events (login, register)
- `xianyu.log` - Xianyu WebSocket module logs
- `error.log` - Error logs only (JSON format)

### Features

- **Request ID Tracking**: Each HTTP request gets a unique ID (8 chars) returned in `X-Request-ID` header
- **User Context**: Authenticated requests include `user_id` in logs
- **Structured JSON**: Error logs use JSON format for easy parsing
- **Log Rotation**: Files rotate at 10MB with 5 backups

### Usage

```python
from ..utils.logger import get_logger

logger = get_logger("module_name", log_file="app.log")
logger.info("message", extra={"extra_data": {"key": "value"}})
```

## Backend API

### Auth API
- `POST /auth/register` - Register new user (body: `{username, password}`)
- `POST /auth/login` - Login (body: `{username, password}`)
- `GET /auth/settings/{username}` - Get user settings (requires auth, own user only)
- `PUT /auth/settings/{username}` - Update user settings (requires auth, own user only)

### Xianyu Account API (requires auth)
- `GET /xianyu-accounts/` - List current user's accounts
- `GET /xianyu-accounts/{id}` - Get account by ID (own account only)
- `POST /xianyu-accounts/` - Create account (auto-associated to current user)
- `PUT /xianyu-accounts/{id}` - Update account (own account only)
- `DELETE /xianyu-accounts/{id}` - Delete account (own account only)
- `POST /xianyu-accounts/{id}/start` - Start WebSocket client for account
- `POST /xianyu-accounts/{id}/stop` - Stop WebSocket client for account

### Product API (requires auth)
- `GET /products/` - List products (own accounts only)
- `GET /products/{id}` - Get product by ID (own product only)
- `POST /products/` - Create product
- `PUT /products/{id}` - Update product
- `PUT /products/{id}/prompt` - Update product prompt
- `POST /products/sync` - Sync product from Xianyu
- `DELETE /products/{id}` - Delete product

### Session API (requires auth)
- `GET /sessions/` - List sessions (own accounts only)
- `GET /sessions/{id}` - Get session by ID
- `POST /sessions/` - Create/update session
- `PUT /sessions/{id}` - Update session
- `DELETE /sessions/{id}` - Delete session (cascades to messages)
- `GET /sessions/{id}/messages` - Get session messages (`limit`, `offset`)
- `GET /sessions/messages/recent` - Get recent messages (`limit`)
- `POST /sessions/messages` - Create message

## Database Schema

### users
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| username | TEXT | UNIQUE NOT NULL |
| password_hash | TEXT | NOT NULL (bcrypt, supports legacy SHA256) |
| role | TEXT | DEFAULT 'common' |
| manual_timeout | INTEGER | DEFAULT 3600 |
| manual_keywords | TEXT | DEFAULT '。' |
| manual_exit_keywords | TEXT | DEFAULT '退出' |

### xianyu_accounts
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| user_id | INTEGER | FOREIGN KEY -> users.id |
| xianyu_name | TEXT | NOT NULL |
| cookie | TEXT | |
| user_agent | TEXT | |

### products
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| xianyu_account_id | INTEGER | FOREIGN KEY -> xianyu_accounts.id |
| item_id | TEXT | UNIQUE with xianyu_account_id |
| title | TEXT | |
| description | TEXT | |
| images | TEXT | JSON array |
| skus | TEXT | JSON array |
| main_prompt | TEXT | |

### sessions
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| xianyu_account_id | INTEGER | FOREIGN KEY -> xianyu_accounts.id |
| chat_id | TEXT | UNIQUE with xianyu_account_id |
| user_id | TEXT | |
| user_name | TEXT | |
| item_id | TEXT | |
| last_message_time | INTEGER | |
| created_at | INTEGER | |
| updated_at | INTEGER | |

### messages
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| session_id | INTEGER | FOREIGN KEY -> sessions.id |
| xianyu_account_id | INTEGER | FOREIGN KEY -> xianyu_accounts.id |
| is_outgoing | INTEGER | DEFAULT 0 |
| sender_id | TEXT | |
| sender_name | TEXT | |
| content | TEXT | |
| message_type | TEXT | DEFAULT 'chat' |
| created_at | INTEGER | |

## Key Dependencies

**Frontend**: vue@3, vue-router, element-plus, axios, vite
**Backend**: fastapi, uvicorn, pydantic, python-dotenv, python-jose[cryptography], passlib[bcrypt], websockets (for Xianyu connection), requests

## Core WebSocket Flow

1. User adds Xianyu account (cookie) via web UI
2. System creates WSClient with cookie and connects to `wss://wss-goofish.dingtalk.com/`
3. WSClient handles:
   - Token refresh (via XianyuApis)
   - Heartbeat (XianyuHeartbeat)
   - Message receiving & parsing (XianyuMessageParser)
   - Message handling (XianyuMessageHandler): saves to DB, handles orders, auto-reply logic
   - Manual takeover mode (ManualModeManager): triggered by keywords like "。" to pause auto-reply
4. Frontend polls/retrieves messages via REST API
