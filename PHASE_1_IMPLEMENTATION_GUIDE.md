# PHASE 1: SEMANTIC FOUNDATIONS - IMPLEMENTATION GUIDE

## Overview

Transform memory from substring search to semantic vector search. This enables:
- Finding relevant memories by meaning, not keywords
- Automated memory consolidation (merge similar memories)
- Deduplication and redundancy elimination
- Faster response times (< 100ms vs linear scan)

## Timeline: 2 weeks | Effort: 40 hours

---

## STEP 1: Qdrant Integration (Day 1-2)

### 1.1 Docker Compose Setup

Update docker-compose.yml:

\\\yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      QDRANT_API_KEY: \
    networks:
      - jarvis-network

volumes:
  qdrant_data:
    driver: local

networks:
  jarvis-network:
    driver: bridge
\\\

### 1.2 Python Dependencies

Update equirements.txt:
\\\
qdrant-client>=2.7.0
openai>=1.3.0
PyYAML>=6.0
\\\

---

## STEP 2: Embedding Service (Day 2-3)

Create services/gateway/src/embeddings.py:

\\\python
from typing import List
from openai import OpenAI
import numpy as np

class EmbeddingService:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def embed_text(self, text: str) -> List[float]:
        """Embed single text."""
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts efficiently."""
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]
    
    def embed_with_metadata(self, texts: List[str]) -> dict:
        """Embed with tokens count."""
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return {
            'embeddings': [item.embedding for item in response.data],
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens,
                'total_tokens': response.usage.total_tokens
            }
        }
\\\

---

## STEP 3: Vector Memory Manager (Day 3-4)

Create services/gateway/src/vector_memory.py:

\\\python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Optional
from embeddings import EmbeddingService

class VectorMemoryManager:
    def __init__(self, qdrant_url: str, embedding_service: EmbeddingService):
        self.client = QdrantClient(url=qdrant_url)
        self.embedding_service = embedding_service
        self.collection_name = "memories"
        
        # Ensure collection exists
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if not exists."""
        try:
            self.client.get_collection(self.collection_name)
        except:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1536,  # text-embedding-3-small dimension
                    distance=Distance.COSINE
                )
            )
    
    def add_memory(self, memory_id: str, text: str, metadata: dict) -> bool:
        """Add memory with embedding."""
        embedding = self.embedding_service.embed_text(text)
        point = PointStruct(
            id=hash(memory_id) % (2**32),
            vector=embedding,
            payload={
                'memory_id': memory_id,
                'text': text,
                **metadata
            }
        )
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        return True
    
    def search_memories(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[dict]:
        """Semantic search memories."""
        query_embedding = self.embedding_service.embed_text(query)
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=threshold
        )
        return [
            {
                'memory_id': r.payload['memory_id'],
                'text': r.payload['text'],
                'score': r.score,
                'metadata': {k: v for k, v in r.payload.items() 
                            if k not in ['memory_id', 'text']}
            }
            for r in results
        ]
    
    def batch_add_memories(self, memories: List[dict]) -> bool:
        """Batch insert memories efficiently."""
        embeddings = self.embedding_service.embed_batch(
            [m['text'] for m in memories]
        )
        points = [
            PointStruct(
                id=hash(m['id']) % (2**32),
                vector=emb,
                payload={
                    'memory_id': m['id'],
                    'text': m['text'],
                    **m.get('metadata', {})
                }
            )
            for m, emb in zip(memories, embeddings)
        ]
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        return True
\\\

---

## STEP 4: Update Memory Endpoint (Day 4-5)

Modify services/gateway/src/main.py:

\\\python
from vector_memory import VectorMemoryManager
from embeddings import EmbeddingService

# Initialize services
embedding_service = EmbeddingService(
    api_key=settings.OPENAI_API_KEY
)
vector_memory = VectorMemoryManager(
    qdrant_url=settings.QDRANT_URL,
    embedding_service=embedding_service
)

@app.post("/api/v1/memory/search")
async def search_memories(query: str, top_k: int = 5):
    """Semantic memory search."""
    results = vector_memory.search_memories(query, top_k)
    return {
        'results': results,
        'query': query,
        'count': len(results)
    }

@app.post("/api/v1/memory/add")
async def add_memory(memory: MemoryEntry):
    """Add memory with automatic embedding."""
    success = vector_memory.add_memory(
        memory_id=str(memory.id),
        text=memory.content,
        metadata={
            'category': memory.category,
            'timestamp': memory.created_at.isoformat()
        }
    )
    # Also store in SQL for durability
    db.session.add(memory)
    db.session.commit()
    return {'success': success, 'memory_id': memory.id}
\\\

---

## STEP 5: Feedback Processing Loop (Day 5-6)

Create services/gateway/src/feedback_processor.py:

\\\python
from typing import List
from sqlalchemy import select
from models import ConversationFeedback, MemoryEntry

class FeedbackProcessor:
    def __init__(self, db_session, vector_memory):
        self.db = db_session
        self.vector_memory = vector_memory
    
    def process_unprocessed_feedback(self):
        """Process feedback data for learning."""
        feedback_items = self.db.query(ConversationFeedback).filter(
            ConversationFeedback.processed == False
        ).all()
        
        learnings = []
        for feedback in feedback_items:
            if feedback.rating < 3:  # Negative feedback
                learning = {
                    'type': 'error_correction',
                    'conversation_id': feedback.conversation_id,
                    'rating': feedback.rating,
                    'comment': feedback.comment,
                    'timestamp': feedback.created_at
                }
                learnings.append(learning)
        
        return learnings
    
    def consolidate_similar_memories(self, threshold: float = 0.95):
        """Merge similar memories to reduce redundancy."""
        memories = self.db.query(MemoryEntry).all()
        merged_count = 0
        
        for i, mem1 in enumerate(memories):
            for mem2 in memories[i+1:]:
                results = self.vector_memory.search_memories(
                    query=mem1.content,
                    top_k=1,
                    threshold=threshold
                )
                if results and results[0]['memory_id'] == mem2.id:
                    # Merge these memories
                    merged_count += 1
        
        return merged_count
\\\

---

## STEP 6: Database Migration (Day 6-7)

Create migration lembic/versions/add_embeddings.py:

\\\python
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('memory_entries', 
        sa.Column('embedding', sa.JSON, nullable=True)
    )
    op.add_column('memory_entries',
        sa.Column('embedding_model', sa.String(50), nullable=True)
    )
    op.create_index('idx_memory_category', 'memory_entries', ['category'])

def downgrade():
    op.drop_index('idx_memory_category')
    op.drop_column('memory_entries', 'embedding_model')
    op.drop_column('memory_entries', 'embedding')
\\\

---

## STEP 7: Testing & Validation (Day 7-8)

Create 	ests/test_vector_memory.py:

\\\python
import pytest
from vector_memory import VectorMemoryManager
from embeddings import EmbeddingService

@pytest.fixture
def embedding_service():
    return EmbeddingService(api_key="test-key")

@pytest.fixture
def vector_memory(embedding_service):
    return VectorMemoryManager(
        qdrant_url="http://localhost:6333",
        embedding_service=embedding_service
    )

def test_semantic_search(vector_memory):
    # Add test memories
    memories = [
        {'id': '1', 'text': 'Python is a programming language'},
        {'id': '2', 'text': 'Java is also a programming language'},
        {'id': '3', 'text': 'The weather is sunny today'}
    ]
    vector_memory.batch_add_memories(memories)
    
    # Search for programming related
    results = vector_memory.search_memories('programming', top_k=2)
    assert len(results) == 2
    assert results[0]['score'] > results[1]['score']

def test_memory_consolidation(vector_memory, feedback_processor):
    # Add similar memories
    memories = [
        {'id': '1', 'text': 'User likes Python for backend'},
        {'id': '2', 'text': 'Python is good for server development'}
    ]
    vector_memory.batch_add_memories(memories)
    
    # Consolidate
    merged = feedback_processor.consolidate_similar_memories(threshold=0.9)
    assert merged > 0
\\\

---

## DEPLOYMENT CHECKLIST

- [ ] Docker image with Qdrant running
- [ ] OpenAI API key configured
- [ ] Qdrant collection created
- [ ] Memory embeddings populated
- [ ] Search endpoint tested (< 100ms latency)
- [ ] Feedback loop processing
- [ ] Memory consolidation working
- [ ] All tests passing

---

## SUCCESS CRITERIA

| Metric | Target | Current |
|---|---|---|
| Semantic Search NDCG@10 | > 0.8 | - |
| Query Latency | < 100ms | - |
| Memory Dedup Rate | > 80% | - |
| Feedback Processing | 100% | 0% |

