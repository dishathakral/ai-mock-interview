"""
Initial setup and database testing
Run this first to verify database connections
"""

import sys

sys.path.insert(0, '/Users/disha/PycharmProjects/ai-mock-interview')

from sqlalchemy import text  # ADD THIS IMPORT
from app.database.postgres_db import engine, SessionLocal, init_db
from app.database.chroma_db import chroma_db
from app.database.models import GlobalQuestion
from app.services.question_service import QuestionService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_database_setup():
    """Test database initialization and connections"""

    print("\n" + "=" * 60)
    print("TESTING DATABASE SETUP")
    print("=" * 60 + "\n")

    # 1. Test PostgreSQL Connection
    print("1️⃣ Testing PostgreSQL connection...")
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))  # WRAP WITH text()
            print("✅ PostgreSQL connected successfully!")
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

    # 2. Create Tables
    print("\n2️⃣ Creating database tables...")
    try:
        init_db()
        print("   ✅ All tables created successfully!")
    except Exception as e:
        print(f"   ❌ Table creation failed: {e}")
        return False

    # 3. Test ChromaDB
    print("\n3️⃣ Testing ChromaDB connection...")
    try:
        count = chroma_db.get_collection_count()
        print(f"   ✅ ChromaDB connected! Current question count: {count}")
    except Exception as e:
        print(f"   ❌ ChromaDB connection failed: {e}")
        return False

    # 4. Load Static Questions
    print("\n4️⃣ Loading static questions...")
    db = SessionLocal()
    try:
        # Check if questions already loaded
        existing_count = db.query(GlobalQuestion).count()
        if existing_count > 0:
            print(f"   ℹ️  Questions already loaded ({existing_count} existing)")
            print("   Skipping load to avoid duplicates")
        else:
            count = QuestionService.load_static_questions(
                db,
                "/Users/disha/PycharmProjects/ai-mock-interview/data/static_questions.json"
            )
            print(f"   ✅ Loaded {count} static questions!")

        # Verify in database
        total = db.query(GlobalQuestion).count()
        print(f"   📊 Total questions in PostgreSQL: {total}")

        vector_count = chroma_db.get_collection_count()
        print(f"   📊 Total questions in ChromaDB: {vector_count}")

        # Show breakdown by subcategory
        stats = QuestionService.get_question_stats(db)
        print(f"\n   📈 Question Breakdown:")
        for subcategory, count in stats['by_subcategory'].items():
            print(f"      • {subcategory}: {count} questions")
        print(f"      • Mandatory: {stats['mandatory']} questions")

    except Exception as e:
        print(f"   ❌ Error loading questions: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED! Database setup complete.")
    print("=" * 60 + "\n")
    return True


if __name__ == "__main__":
    success = test_database_setup()
    sys.exit(0 if success else 1)
