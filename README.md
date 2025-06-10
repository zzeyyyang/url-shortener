# URL Shortener

A simple and efficient URL shortening service built with FastAPI and SQLite.

## Features

- Shorten long URLs to manageable links
- Redirect short URLs to their original destinations
- Clean and modern web interface
- Fast and lightweight

## Tech Stack

- FastAPI - Modern, fast web framework for building APIs
- SQLite - Lightweight database for storing URL mappings
- Uvicorn - ASGI server for running the application

## Prerequisites

- Python 3.7+
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/url-shortener.git
cd url-shortener
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the server:
```bash
python main.py
```

2. Open your browser and navigate to:
```
http://127.0.0.1:8000
```

## Project Structure

```
url-shortener/
├── main.py           # Main application file
├── db.py            # Database operations
├── models.py        # Data models
├── routers/         # API routes
│   ├── shorten.py   # URL shortening endpoints
│   └── redirect.py  # URL redirection endpoints
├── static/          # Static files (HTML, CSS, JS)
└── requirements.txt # Project dependencies
```

## Development

The application runs in development mode by default with hot-reload enabled. For production deployment, set `reload=False` in `main.py`.

## License

This project is open source and available under the MIT License. 