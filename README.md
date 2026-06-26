# MedAssist AI 🩺

An AI-powered medical information assistant built with Claude on Azure AI Foundry. Provides evidence-based information about symptoms, diseases, medications, and treatment guidelines.

> ⚠️ **Disclaimer:** This application is for **educational purposes only** and does not constitute medical advice. Always consult a qualified healthcare professional.

## Live Demo

🌐 **[https://medical-agent-jqlj.onrender.com](https://medical-agent-jqlj.onrender.com)**

## Features

- 🔍 **Symptom & Disease Search** — Powered by EndlessMedical database via Azure AI Search
- 💊 **Drug Information** — Real-time FDA drug data via OpenFDA API
- 📋 **Treatment Guidelines** — Evidence-based protocols for common conditions stored in Azure Blob Storage
- 💬 **Conversational AI** — Multi-turn chat with session memory powered by Claude
- 🚨 **Safety First** — Built-in emergency detection and medical disclaimers

## Tech Stack

| Layer | Technology |
|---|---|
| AI Model | Claude Haiku 4.5 via Azure AI Foundry |
| Backend | FastAPI (Python) |
| Knowledge Base | Azure AI Search |
| Document Storage | Azure Blob Storage |
| Drug Data | OpenFDA API (free, no key needed) |
| Frontend | Vanilla HTML/CSS/JS |
| Hosting | Render (free tier) |

## Architecture

```
User → Render (FastAPI) → Claude Haiku 4.5 (Azure AI Foundry)
                        → Azure AI Search (diseases & symptoms)
                        → Azure Blob Storage (treatment guidelines)
                        → OpenFDA API (drug information)
```

## Getting Started

### Prerequisites

- Python 3.11+
- Azure account with:
  - Azure AI Foundry resource with Claude deployed
  - Azure AI Search service
  - Azure Blob Storage account

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Sarthakhatwar1606/medical-agent.git
   cd medical-agent
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Fill in your Azure credentials in `.env`.

5. **Run the app**
   ```bash
   python main.py
   ```

6. Open **http://localhost:8000** in your browser.

### Environment Variables

| Variable | Description |
|---|---|
| `AZURE_AI_FOUNDRY_ENDPOINT` | Azure AI Foundry resource endpoint |
| `AZURE_AI_FOUNDRY_API_KEY` | Azure AI Foundry API key |
| `CLAUDE_MODEL` | Model name (e.g. `claude-haiku-4-5`) |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint URL |
| `AZURE_SEARCH_KEY` | Azure AI Search admin key |
| `AZURE_SEARCH_INDEX` | Search index name (default: `medical-knowledge`) |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Blob Storage connection string |
| `AZURE_STORAGE_CONTAINER` | Container name (default: `medical-documents`) |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Send a message to the medical agent |
| `DELETE` | `/chat/{session_id}` | Clear conversation history |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive API documentation |

### Example Request

```bash
curl -X POST https://medical-agent-jqlj.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the symptoms of diabetes?"}'
```

## Project Structure

```
medical-agent/
├── agent.py          # Core AI agent logic
├── config.py         # Environment variable management
├── main.py           # FastAPI server
├── tools.py          # Azure Search, OpenFDA, Blob Storage tools
├── requirements.txt  # Python dependencies
├── render.yaml       # Render deployment config
├── static/
│   └── index.html    # Chat UI frontend
└── .env.example      # Environment variables template
```

## Deployment

### Render (recommended — free)

1. Fork this repository
2. Create a new Web Service on [render.com](https://render.com)
3. Connect your GitHub repo
4. Add environment variables in the Render dashboard
5. Deploy

### Local Development

```bash
source venv/bin/activate
python main.py
```

## Safety & Ethics

- All responses include a medical disclaimer
- Emergency symptoms trigger immediate advice to call emergency services
- The agent is explicitly instructed not to replace professional medical advice
- Extra caution for vulnerable populations (children, elderly, pregnant women)

## License

MIT License — feel free to use and modify.
