# app/database/chroma_db.py

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ChromaDBManager:
    """Singleton class to manage ChromaDB connections"""

    _instance = None
    _client = None
    _collection = None
    _embedding_model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaDBManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize ChromaDB client and embedding model"""
        try:
            # Create persistent ChromaDB client
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Load embedding model (lightweight and fast)
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

            # Create or get collection
            self._collection = self._client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"description": "Interview questions embeddings"}
            )

            logger.info(f"ChromaDB initialized successfully with {self.get_collection_count()} questions")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text"""
        embedding = self._embedding_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def add_question(
            self,
            question_id: int,
            question_text: str,
            question_type: str,
            industry: str = "general",
            job_role: str = "general",
            difficulty: str = "medium",
            tags: Optional[List[str]] = None,
            subcategory: Optional[str] = None,
            is_static: int = 0
    ):
        """
        Add question to vector database with comprehensive metadata

        Args:
            question_id: Unique ID from PostgreSQL
            question_text: The question content
            question_type: hr, technical, behavioral
            industry: Industry category
            job_role: Job role category
            difficulty: easy, medium, hard
            tags: List of tags for the question
            subcategory: Subcategory (introductory, behavioral, etc.)
            is_static: 1 for static questions, 0 for generated
        """
        try:
            embedding = self.generate_embedding(question_text)

            # Prepare metadata (ChromaDB requires string/int/float values)
            metadata = {
                "question_id": str(question_id),
                "question_type": question_type,
                "industry": industry,
                "job_role": job_role,
                "difficulty": difficulty,
                "tags": ",".join(tags) if tags else "",  # Store as comma-separated string
                "subcategory": subcategory or "general",
                "is_static": is_static
            }

            self._collection.add(
                ids=[str(question_id)],
                embeddings=[embedding],
                documents=[question_text],
                metadatas=[metadata]
            )
            logger.info(f"Added question {question_id} to ChromaDB")
        except Exception as e:
            logger.error(f"Error adding question to ChromaDB: {e}")
            raise

    def find_similar_questions(
            self,
            question_text: str,
            n_results: int = 5,
            threshold: float = 0.85
    ) -> List[Dict]:
        """
        Find similar questions using cosine similarity
        Returns questions with similarity >= threshold

        Used for: Duplicate detection
        """
        try:
            embedding = self.generate_embedding(question_text)

            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )

            # Convert ChromaDB results to structured format
            similar_questions = []

            if results['ids'] and len(results['ids'][0]) > 0:
                for i, question_id in enumerate(results['ids'][0]):
                    # ChromaDB returns L2 distance, convert to similarity
                    distance = results['distances'][0][i]
                    similarity = 1 - (distance / 2)  # Approximate cosine similarity

                    if similarity >= threshold:
                        similar_questions.append({
                            'question_id': int(question_id),
                            'question_text': results['documents'][0][i],
                            'similarity': similarity,
                            'metadata': results['metadatas'][0][i]
                        })

            logger.info(f"Found {len(similar_questions)} similar questions above threshold {threshold}")
            return similar_questions

        except Exception as e:
            logger.error(f"Error finding similar questions: {e}")
            return []

    def check_duplicate_question(
            self,
            question_text: str,
            question_type: str,
            threshold: float = 0.85
    ) -> Optional[Dict]:
        """
        Purpose 2: Duplicate Detection
        Check if question already exists with high similarity
        Returns the first duplicate found, or None

        Args:
            question_text: The new question to check
            question_type: Filter by question type (hr, technical, behavioral)
            threshold: Similarity threshold (0.85 = 85% similar)

        Returns:
            Dict with duplicate question info, or None if unique
        """
        try:
            embedding = self.generate_embedding(question_text)

            # Search only within same question type
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=5,  # Check top 5 most similar
                where={"question_type": question_type},
                include=["documents", "metadatas", "distances"]
            )

            # Check if any result exceeds similarity threshold
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    distance = results['distances'][0][i]
                    similarity = 1 - (distance / 2)

                    if similarity >= threshold:
                        logger.info(f"Found duplicate question (similarity: {similarity:.3f})")
                        return {
                            'question_id': int(results['ids'][0][i]),
                            'question_text': results['documents'][0][i],
                            'similarity': similarity,
                            'metadata': results['metadatas'][0][i]
                        }

            logger.info("No duplicate found - question is unique")
            return None

        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return None

    def find_questions_by_user_profile(
            self,
            user_skills: Optional[str] = None,
            user_bio: Optional[str] = None,
            industry_insight: Optional[str] = None,
            experience: Optional[str] = None,
            question_type: str = "technical",
            difficulty: Optional[str] = None,
            industry: Optional[str] = None,
            job_role: Optional[str] = None,
            n_results: int = 10
    ) -> List[Dict]:
        """
        Purpose 1: Semantic Question Retrieval
        Find questions semantically similar to user's profile

        Args:
            user_skills: User's skills (e.g., "Python, ML, NLP")
            user_bio: User's bio description
            industry_insight: User's industry knowledge
            experience: User's experience level
            question_type: Filter by type (hr, technical, behavioral)
            difficulty: Filter by difficulty (easy, medium, hard)
            industry: Filter by industry
            job_role: Filter by job role
            n_results: Number of questions to return

        Returns:
            List of questions matching user profile semantically
        """
        try:
            # Combine user profile fields into single text
            profile_parts = []
            if user_skills:
                profile_parts.append(user_skills)
            if user_bio:
                profile_parts.append(user_bio)
            if industry_insight:
                profile_parts.append(industry_insight)
            if experience:
                profile_parts.append(experience)

            user_profile_text = " ".join(profile_parts)

            if not user_profile_text.strip():
                logger.warning("Empty user profile provided")
                return []

            # Generate embedding for user profile
            profile_embedding = self.generate_embedding(user_profile_text)

            # Build metadata filter
            where_filter = {"question_type": question_type}
            if difficulty:
                where_filter["difficulty"] = difficulty
            if industry:
                where_filter["industry"] = industry
            if job_role:
                where_filter["job_role"] = job_role

            # Query ChromaDB with metadata filtering
            results = self._collection.query(
                query_embeddings=[profile_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            matched_questions = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i, question_id in enumerate(results['ids'][0]):
                    distance = results['distances'][0][i]
                    similarity = 1 - (distance / 2)

                    matched_questions.append({
                        'question_id': int(question_id),
                        'question_text': results['documents'][0][i],
                        'similarity': similarity,
                        'metadata': results['metadatas'][0][i]
                    })

            logger.info(f"Found {len(matched_questions)} questions matching user profile")
            return matched_questions

        except Exception as e:
            logger.error(f"Error finding questions by user profile: {e}")
            return []

    def query_with_filters(
            self,
            query_text: str,
            filters: Dict,
            n_results: int = 10
    ) -> List[Dict]:
        """
        Advanced querying with complex metadata filters

        Example filters:
        - {"question_type": "technical", "difficulty": "medium"}
        - {"industry": "tech", "job_role": "software_engineer"}
        - {"$and": [{"difficulty": "medium"}, {"is_static": 0}]}

        Args:
            query_text: Text to search for
            filters: Dictionary of metadata filters
            n_results: Number of results to return

        Returns:
            List of matched questions with similarity scores
        """
        try:
            embedding = self.generate_embedding(query_text)

            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                where=filters,
                include=["documents", "metadatas", "distances"]
            )

            matched_questions = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i, question_id in enumerate(results['ids'][0]):
                    distance = results['distances'][0][i]
                    similarity = 1 - (distance / 2)

                    matched_questions.append({
                        'question_id': int(question_id),
                        'question_text': results['documents'][0][i],
                        'similarity': similarity,
                        'metadata': results['metadatas'][0][i]
                    })

            logger.info(f"Query with filters returned {len(matched_questions)} results")
            return matched_questions

        except Exception as e:
            logger.error(f"Error querying with filters: {e}")
            return []

    def get_questions_by_filters(
            self,
            question_type: Optional[str] = None,
            difficulty: Optional[str] = None,
            industry: Optional[str] = None,
            job_role: Optional[str] = None,
            is_static: Optional[int] = None,
            limit: int = 100
    ) -> List[Dict]:
        """
        Get questions by metadata filters only (no semantic search)

        Args:
            question_type: Filter by question type
            difficulty: Filter by difficulty
            industry: Filter by industry
            job_role: Filter by job role
            is_static: Filter by static flag
            limit: Maximum number of questions to return

        Returns:
            List of questions matching filters
        """
        try:
            # Build where filter
            where_filter = {}
            if question_type:
                where_filter["question_type"] = question_type
            if difficulty:
                where_filter["difficulty"] = difficulty
            if industry:
                where_filter["industry"] = industry
            if job_role:
                where_filter["job_role"] = job_role
            if is_static is not None:
                where_filter["is_static"] = is_static

            if not where_filter:
                logger.warning("No filters provided, returning empty list")
                return []

            # Get all matching documents
            results = self._collection.get(
                where=where_filter,
                limit=limit,
                include=["documents", "metadatas"]
            )

            matched_questions = []
            if results['ids']:
                for i, question_id in enumerate(results['ids']):
                    matched_questions.append({
                        'question_id': int(question_id),
                        'question_text': results['documents'][i],
                        'metadata': results['metadatas'][i]
                    })

            logger.info(f"Retrieved {len(matched_questions)} questions by filters")
            return matched_questions

        except Exception as e:
            logger.error(f"Error getting questions by filters: {e}")
            return []

    def get_collection_count(self) -> int:
        """Get total number of questions in vector database"""
        try:
            return self._collection.count()
        except Exception as e:
            logger.error(f"Error getting collection count: {e}")
            return 0

    def delete_question(self, question_id: int):
        """Remove question from vector database"""
        try:
            self._collection.delete(ids=[str(question_id)])
            logger.info(f"Deleted question {question_id} from ChromaDB")
        except Exception as e:
            logger.error(f"Error deleting question from ChromaDB: {e}")

    def update_question(
            self,
            question_id: int,
            question_text: Optional[str] = None,
            metadata: Optional[Dict] = None
    ):
        """
        Update existing question in ChromaDB

        Args:
            question_id: ID of question to update
            question_text: New question text (will regenerate embedding)
            metadata: New metadata to update
        """
        try:
            update_params = {"ids": [str(question_id)]}

            if question_text:
                embedding = self.generate_embedding(question_text)
                update_params["embeddings"] = [embedding]
                update_params["documents"] = [question_text]

            if metadata:
                update_params["metadatas"] = [metadata]

            self._collection.update(**update_params)
            logger.info(f"Updated question {question_id} in ChromaDB")
        except Exception as e:
            logger.error(f"Error updating question in ChromaDB: {e}")
            raise

    def reset_collection(self):
        """
        Delete all questions from collection
        USE WITH CAUTION - Only for development
        """
        try:
            self._client.delete_collection(name=settings.CHROMA_COLLECTION_NAME)
            self._collection = self._client.create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"description": "Interview questions embeddings"}
            )
            logger.warning("ChromaDB collection reset - all questions deleted")
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            raise

    def query_similar_questions(
            self,
            embedding: List[float],
            question_type: Optional[str] = None,
            job_role: Optional[str] = None,
            limit: int = 5,
            threshold: float = 0.75
    ) -> List[Dict]:
        """
        🔥 PHASE 3: Query similar questions by embedding + filters
        Used by InterviewOrchestrator for profile matching
        """
        try:
            # Build metadata filter
            where_filter = {}
            if question_type:
                where_filter["question_type"] = question_type
            if job_role:
                where_filter["job_role"] = job_role

            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=limit,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )

            # Filter by similarity threshold + format for orchestrator
            similar_questions = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    distance = results['distances'][0][i]
                    similarity = 1 - (distance / 2)  # L2 → cosine

                    if similarity >= threshold:
                        similar_questions.append({
                            'payload': results['metadatas'][0][i],  # For orchestrator
                            'question_id': int(results['ids'][0][i]),
                            'question_text': results['documents'][0][i],
                            'similarity': similarity
                        })

            logger.info(f"🔍 Chroma query: {len(similar_questions)} results (threshold={threshold})")
            return similar_questions

        except Exception as e:
            logger.error(f"Error in query_similar_questions: {e}")
            return []


# Create singleton instance
chroma_db = ChromaDBManager()
