import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from routers import shorten, redirect

app = FastAPI()

app.include_router(shorten.router)

@app.get("/")
async def read_index():
    with open("static/index.html") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, headers={"Cache-Control": "no-cache"})

# Mount the static directory AFTER the specific static file routes
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(redirect.router)

if __name__ == "__main__":
    # The `reload=True` parameter is for development purposes.
    # In a production environment, this should be False.
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
