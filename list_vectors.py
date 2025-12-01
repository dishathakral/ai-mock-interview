from app.database.chroma_db import chroma_db

def list_vector_questions(limit=150):
    """
    List up to 'limit' vector questions with metadata to check if question_id is present.
    """
    try:
        results = chroma_db._collection.get(
            limit=limit,
            include=["metadatas", "documents"]  # Use 'include' list instead of include_metadata/include_documents
        )
        for idx, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
            print(f"#{idx+1} Question ID: {meta.get('question_id', 'N/A')}")
            print(f"Text snippet: {doc[:100]}...")
            print(f"Metadata: {meta}")
            print("-" * 60)
    except Exception as e:
        print(f"Error fetching questions from vector DB: {e}")

if __name__ == "__main__":
    list_vector_questions()
