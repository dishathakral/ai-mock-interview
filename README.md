# AI Mock Interview Platform 🧠💼

An intelligent interview simulation platform powered by FastAPI, PostgreSQL, ChromaDB vector search, and Google Gemini AI.

[![Python](https://img.shields.io/badge/Python-3.13%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-brightgreen)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-green)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🚀 Quick Start

git clone https://github.com/dishathakral/ai-mock-interview.git
cd ai-mock-interview
python3.13 -m venv .venv
source .venv/bin/activate # Linux/macOS

.venv\Scripts\activate # Windows PowerShell
pip install -r requirements.txt
cp .env.example .env # Edit with your credentials
createdb interview_db
python scripts/generate_static_questions_simple.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

text

**API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📋 Setup Instructions

### Prerequisites

- Python 3.13+
- PostgreSQL 16+ (running)
- Git

### Step-by-Step Setup

#### 1. Clone & Setup Environment

git clone https://github.com/dishathakral/ai-mock-interview.git
cd ai-mock-interview
python3.13 -m venv .venv
source .venv/bin/activate # Linux/macOS

.venv\Scripts\activate # Windows PowerShell
text

#### 2. Install Dependencies

pip install --upgrade pip
pip install -r requirements.txt

text

#### 3. Configure Environment Variables

Copy the example config and update it:

cp .env.example .env

text

Edit `.env` with your actual PostgreSQL credentials, Gemini API key, and other configs.

---

#### 4. Example `.env.example`

PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=interview_db

ChromaDB Configuration
CHROMA_PERSIST_DIR=./chroma_data
CHROMA_COLLECTION_NAME=interview_questions

Application Settings
API_VERSION=v1
DEBUG=True

Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

text

---

#### 5. Create PostgreSQL Database

createdb interview_db

text

#### 6. Initialize Database Tables

If using migrations, run them.

Otherwise, initialize tables manually:

python -c "from app.database.postgres_db import Base, engine; Base.metadata.create_all(bind=engine)"

text

#### 7. Load Static Interview Questions

python scripts/generate_static_questions_simple.py

text

#### 8. Run the API Server

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

text

#### 9. Run Tests

Make sure your server is running, then run tests:

python test_phase1_complete.py
python test_phase2.py

text

---

## 🎯 Features Summary (up to Phase 2)

| Phase       | Features                                                  |
|-------------|-----------------------------------------------------------|
| Phase 1     | User CRUD, Interview lifecycle, Static questions, ChromaDB vector search |
| Phase 2     | AI-generated HR/Technical/Experience questions using user profiles, Gemini integration |

---

## 🧪 API Endpoints

- `POST /api/v1/users/` - Create user
- `POST /api/v1/questions/generate/hr` - Generate HR question by user profile
- `POST /api/v1/questions/generate/technical` - Generate Technical question by user profile
- `POST /api/v1/questions/generate/experience` - Generate personalized experience question
- `POST /api/v1/questions/check-similarity` - Check question similarity with vector DB

---

## Notes

- The `chroma_data/` directory stores local vector DB files and is excluded from Git.
- `.env` contains sensitive data and **must not** be committed (see `.env.example` template).
- Gemini API key is optional for Phase 2 but required for AI question generation.
- For production, set environment variables securely and configure Postgres accordingly.

---

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to your branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- FastAPI
- PostgreSQL
- ChromaDB
- Google Gemini
- Sentence Transformers

---

**Made with ❤️ by [Disha Thakral](https://github.com/dishathakral)**
