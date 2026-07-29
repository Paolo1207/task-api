# main.py
from fastapi import FastAPI
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Task API", version="1.0")

@app.get("/")
def hello():
    return {"message": "Hello, world!"}

app = FastAPI(title="Task API", version="1.0")

@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health")
def health():
    return {"status": "ok"}

app = FastAPI(title="Task API", version="1.0")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

tasks = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Write README", "done": False},
    {"id": 3, "title": "Walk the dog", "done": True},
]
next_id = 4

@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health")
def health():
    return {"status": "ok"}

def find_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None

@app.get("/tasks")
def list_tasks():
    return tasks

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task