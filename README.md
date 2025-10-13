# Financial Advisor AI

A next-generation AI assistant for financial advisors, combining LLMs, RAG, and deep integrations with Gmail, Google Calendar, and HubSpot CRM.

## What is Financial Advisor AI?

Financial Advisor AI is a platform that automates and augments the daily workflow of financial advisors using advanced artificial intelligence. It connects to your email, calendar, and CRM, proactively processes events, and enables natural language interaction with all your client data.

## Key Capabilities

- **AI-Powered Chat**: Natural language chat interface powered by OpenAI LLMs (GPT-4o, etc.)
- **Retrieval-Augmented Generation (RAG)**: Combines LLMs with vector search for context-aware answers
- **Memory Rules**: Define automations in natural language ("When I receive an email from a new client, create a HubSpot contact")
- **Webhooks & Event Processing**: Real-time ingestion of Gmail, Google Calendar, and HubSpot events
- **Automated Email & Calendar Management**: Syncs, classifies, and acts on emails and meetings
- **CRM Automation**: Bi-directional sync and automation with HubSpot contacts, deals, and notes
- **Proactive Agent**: LLM can take initiative based on rules, context, and new events
- **Secure OAuth2 Integrations**: Google and HubSpot authentication
- **Streaming Responses**: Real-time, token-by-token chat UX

## Integrations

- **Gmail**: Ingests, classifies, and automates email workflows
- **Google Calendar**: Tracks meetings, sends reminders, and automates scheduling
- **HubSpot CRM**: Syncs contacts, creates notes, updates deals, and more
- **OpenAI**: Uses GPT-4o and embedding models for reasoning and RAG

## Automation Examples

- "When a new email arrives from a prospect, create a HubSpot contact and schedule a follow-up."
- "If a client cancels a meeting, send a personalized reschedule email."
- "When a deal is closed in HubSpot, send a congratulatory email and create a calendar event."
- "Summarize all recent client communications before my next meeting."

## Technical Highlights

- **Backend**: FastAPI (Python 3.13), PostgreSQL + pgvector, async workers, OAuth2
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, streaming chat UI
- **LLM**: OpenAI GPT-4o for chat, text-embedding-3-small for RAG
- **Task System**: Background worker for event-driven automations
- **Security**: All secrets via environment variables, no hardcoded credentials

## Who is it for?

- Financial advisors and wealth managers
- Teams that want to automate client communication and CRM workflows
- Anyone who wants an AI agent that truly understands and acts on their business data

---

> For developer setup, configuration, and API documentation, see:
> - [backend/README.md](backend/README.md)
> - [frontend/README.md](frontend/README.md)

For questions or demo requests, contact the development team.
