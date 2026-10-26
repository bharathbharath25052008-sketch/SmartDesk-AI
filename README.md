# SmartDesk AI 🤖

### Intelligent IT Helpdesk & AI-Powered Troubleshooting System

SmartDesk AI is a web-based IT helpdesk application that helps users create and manage support tickets and receive AI-generated troubleshooting guidance using a locally running Llama 3.2 model.

## ✨ Features

- Create IT support tickets
- Set ticket priorities: Low, Medium, High
- Track ticket statuses: Open, In Progress, Resolved
- Store tickets in an SQLite database
- Get AI-powered troubleshooting suggestions
- Run AI locally using Ollama and Llama 3.2
- Explore API endpoints using FastAPI Swagger documentation
- View ticket statistics on the dashboard

## 🛠️ Technologies Used

- Python
- FastAPI
- SQLite
- HTML, CSS, JavaScript
- Ollama
- Llama 3.2
- Uvicorn

## 🚀 Getting Started

### Prerequisites

Install Python and Ollama. Download the Llama 3.2 model:

```bash
ollama pull llama3.2
```

### Installation

Clone or download this project and open its folder in a terminal.

Create a virtual environment:

```bash
py -3.13 -m venv .venv
```

Install dependencies:

```bash
.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]"
```

Start the application:

```bash
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open the dashboard:

http://127.0.0.1:8000/

Open interactive API documentation:

http://127.0.0.1:8000/docs

## 🤖 AI Troubleshooting

Enter an IT issue, such as:

`My laptop is connected to WiFi but internet is not working.`

SmartDesk AI sends the issue to the locally running Llama 3.2 model and displays suggested causes and troubleshooting steps.

Make sure Ollama is running and the model is available before using this feature.

## 🔌 API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Open dashboard |
| GET | `/api` | API welcome message |
| GET | `/tickets` | List support tickets |
| POST | `/tickets` | Create a ticket |
| PUT | `/tickets/{ticket_id}` | Update ticket status |
| POST | `/ai/troubleshoot` | Get AI troubleshooting |

## 💾 Database

SQLite stores ticket information locally in `smartdesk.db`.

Back up the database before making major changes.

## 🔒 Privacy & Security

- AI troubleshooting is designed to use a local Ollama model.
- Do not upload private ticket data or database backups to a public repository.
- Do not commit virtual environments or sensitive configuration files.

## 🎯 Project Goal

To demonstrate a practical combination of IT service management, REST API development, database operations, and locally hosted AI troubleshooting.

## 👨‍💻 Author

**Bharath P**

*Student Project — AI, Python & IT Support Automation*
