
# Rag Application

A simple RAG (Retrieval-Augmented Generation) app using PDFs and Groq API, with a Gradio interface.

---

## Instructions to Run

### 1. Setup Environment
Create a virtual environment:

```bash
python -m venv pqock_env
```
if you use Linux/macOS
```bash
python3 -m venv pqock_env
```

Activate it:

- **Linux/macOS:**  
```bash
source pqock_env/bin/activate
```

- **Windows:**  
```bash
pqock_env\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```
if you use Linux/macOS
```bash
pip3 install -r requirements.txt
```

---

### 2. Configure

1. Place your PDF documents in the `myrag_app/data/pdfs/` directory.  
2. Set your Groq API key:

- **Linux/macOS:**  
```bash
export GROQ_API_KEY='your_actual_key_here'
```

- **Windows:**  
```bash
set GROQ_API_KEY=your_actual_key_here
```

Or use a `.env` file with [python-dotenv](https://pypi.org/project/python-dotenv/).

---

### 3. Run the Application

```bash
python app.py
```

The Gradio interface URL will be printed in the console, e.g.,  
`Running on public URL: https://...gradio.live`

---

### 4. Run Tests (Optional but Recommended)

1. Ensure you have a small test PDF named `test_document.pdf` in `myrag_app/data/pdfs/`.  
2. Make sure `GROQ_API_KEY` is set (or modify `test_app.py` to skip Groq-related tests if needed).  

Run the test script:

```bash
python test_app.py
```

or using pytest:

```bash
pytest test_app.py
```

---

This structure provides a clear separation of concerns, making the application more maintainable, testable, and suitable for production deployment compared to a single Jupyter Notebook.
