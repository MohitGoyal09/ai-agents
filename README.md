# AI Agents

A curated repository of task-focused AI agents built with modern LLM orchestration frameworks.

## Overview

This repository currently includes:

- **[Scientific Agent](./scientifc_agent/)**  
  A modular research assistant powered by LangGraph that can:
  - understand research questions,
  - search academic papers via the CORE API,
  - analyze PDF content,
  - produce structured, high-quality responses.

## Repository Structure

```text
ai-agents/
├── README.md
└── scientifc_agent/
    ├── agent.py
    ├── models.py
    ├── nodes.py
    ├── prompts.py
    ├── run_scientific_agent.py
    ├── tools.py
    ├── utils.py
    └── requirements.txt
```

## Getting Started

1. Clone the repository:

```bash
git clone https://github.com/MohitGoyal09/ai-agents.git
cd ai-agents
```

2. Install dependencies for the Scientific Agent:

```bash
pip install -r scientifc_agent/requirements.txt
```

3. Configure environment variables (for Scientific Agent):

```env
GOOGLE_API_KEY=your_google_api_key
CORE_API_KEY=your_core_api_key
```

4. Run the Scientific Agent:

```bash
python scientifc_agent/run_scientific_agent.py
```

## Requirements

- Python 3.9+
- API keys for supported model and paper search providers (see above)

## Contributing

Contributions are welcome. To contribute:

1. Fork the repository.
2. Create a feature branch.
3. Commit focused, well-documented changes.
4. Open a pull request with a clear summary.

## License

This project is licensed under the MIT License.
