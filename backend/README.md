# Python Microservice

## Setup

1.  **Navigate to the directory:**
    ```bash
    cd python-backend
    ```

2.  **Create a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Server

Run the following command to start the FastAPI server:

```bash
uvicorn main:app --reload --port 8001
```

The API will be available at `http://localhost:8001`.
- Health check: `http://localhost:8001/health`
- Documentation: `http://localhost:8001/docs`
