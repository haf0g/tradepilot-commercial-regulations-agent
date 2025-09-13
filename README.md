# TradePilot: Agentic AI for Dynamic Trade Regulation Assistance
*A 2025 Capstone Project (PFA) realized at Peaqock Financials*

## Overview

This project, developed as my final year capstone at Peaqock Financials, presents **TradePilot**, an advanced AI-powered assistant designed to simplify access to complex international trade regulations. Unlike traditional static RAG systems, TradePilot leverages an **agentic architecture** powered by **LangGraph**. This allows it to dynamically fetch, process, and analyze relevant trade documents in real-time based on user queries, providing accurate and up-to-date answers without requiring pre-loaded knowledge bases for every possible trade route.

The system integrates seamlessly with the [findrulesoforigin.org](https://findrulesoforigin.org/) platform. When a user asks a question (e.g., "What are the rules of origin for exporting olive oil from Morocco to the USA?"), TradePilot:

1. **Intelligently Parses** the query to extract key details (Exporter, Importer, Product/HS Code).
2. **Automatically Scrapes** the relevant PDF documents (Rules of Origin, Certificates of Origin) from `findrulesoforigin.org` using **Playwright**.
3. **Updates its Knowledge Base** using a hybrid **FAISS/BM25 RAG** system.
4. **Generates a Precise Answer** grounded in the retrieved documents, complete with clickable references to the original sources.

The core technologies used include Python, LangChain, LangGraph, Playwright, FAISS, Sentence-Transformers, and the Groq API for LLM inference.

---

## Key Features Demonstrated in this PFA

* **Agentic AI Workflow:** Implementation of a multi-step, decision-making AI agent using LangGraph.
* **Dynamic Web Scraping:** Automated, headless browser scraping with Playwright to fetch documents on-demand.
* **Advanced RAG Pipeline:** A hybrid retrieval system combining dense (FAISS) and sparse (BM25) methods for improved accuracy.
* **Intelligent Persistence:** Efficient caching mechanism to avoid re-processing unchanged documents, significantly speeding up subsequent queries.
* **Modular Architecture:** Clean separation of concerns (data, retrieval, models, core, orchestrator, UI) for maintainability and scalability.
* **Comprehensive Testing:** Includes a dedicated test suite (`pytest`) covering core components and the agentic workflow.

---

## Instructions to Run

### 1. Setup Environment

Create a virtual environment:

```bash
python -m venv tradepilot_env
# or on Linux/macOS
python3 -m venv tradepilot_env
```

Activate it:

**Linux/macOS**:
```bash
source tradepilot_env/bin/activate
```

**Windows (PowerShell)**:
```powershell
.\tradepilot_env\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
# or on Linux/macOS
pip3 install -r requirements.txt
```

### 2. Configure

Obtain an API key from Groq (or your chosen LLM provider).

Set your Groq API key as an environment variable:

**Linux/macOS**:
```bash
export GROQ_API_KEY='your_actual_groq_api_key_here'
```

**Windows (cmd)**:
```cmd
set GROQ_API_KEY=your_actual_groq_api_key_here
```

Alternatively, you can use a `.env` file with `python-dotenv`.

### 3. Run the Application

```bash
python app.py #or python3 app.py in linux
```

The Gradio interface URL will be printed in the console, e.g., `Running on public URL: https://...gradio.live`.
Navigate to that URL in your browser to interact with TradePilot.

### Running Tests (Highly Recommended)

A comprehensive test suite is included to ensure reliability.

1. Ensure you have a small test PDF named `test_document.pdf` placed in the `tests/` directory.
2. Make sure your `GROQ_API_KEY` environment variable is set.

Run the tests using `pytest`:

```bash
# From the project root directory
pytest
```

## Project Structure Highlights

This architecture cleanly separates different functionalities:

* `app.py`: Main application entry point.
* `config.py`: Centralized configuration.
* `data/`: Modules for loading and preprocessing PDF documents.
* `retrieval/`: RAG components (vector stores, embeddings, hybrid retrieval).
* `models/`: LLM client abstraction (currently Groq).
* `scraper/`: Web scraping logic using Playwright.
* `core/`: The core RAG analyzer logic.
* `orchestrator/`: Heart of the agentic system. Defines tools, workflow nodes, and the LangGraph agent.
* `ui/`: Gradio interface definition.
* `tests/`: Dedicated test suite for principal components.

This modular design makes the application highly maintainable, testable, and far superior to a monolithic Jupyter Notebook approach, making it suitable for future enhancements and production deployment.

---

N'hésitez pas si vous voulez ajouter des détails spécifiques sur des choix techniques, des difficultés rencontrées ou des axes d'amélioration future !

---


**Internship accomplished at**  :
> Peaqock Financials

**Author** :
> Hafid GARHOUM - Big Data Engineering Student - ENSA

**Collaborator** :
> Abdelmoughit AKKAD - M2 Finance et Data Science - UH2 
