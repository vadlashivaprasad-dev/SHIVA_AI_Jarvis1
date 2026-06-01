# MEMORY ARCHITECTURE - COGNITIVE OS DESIGN

## Overview

A complete memory system supporting multiple memory types for true cognitive capability.

## Memory Types

### 1. Working Memory
- Current conversation context
- Tokens: 4K-8K limit
- Duration: Single conversation
- Updated: Every turn
- Purpose: Active reasoning

### 2. Episodic Memory
- Events, conversations, interactions
- Storage: SQL + vector DB
- Retrieval: Semantic + temporal
- Purpose: Remember what happened

### 3. Semantic Memory
- Facts, knowledge, relationships
- Storage: Knowledge graph (Neo4j)
- Retrieval: Graph queries + inference
- Purpose: Understand the world

### 4. Procedural Memory
- Skills, workflows, processes
- Storage: Skill graphs + ML models
- Retrieval: Context matching
- Purpose: Execute complex tasks

### 5. Affective Memory
- Preferences, emotions, goals
- Storage: User profile + embeddings
- Retrieval: User modeling
- Purpose: Personalization

---

## Implementation

### Database Schema

\\\sql
-- Episodic memories (with embeddings)
CREATE TABLE episodic_memories (
    id UUID PRIMARY KEY,
    user_id UUID,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    timestamp TIMESTAMP,
    tags TEXT[],
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Semantic facts (entities and relationships)
CREATE TABLE semantic_facts (
    id UUID PRIMARY KEY,
    subject TEXT,
    predicate TEXT,
    object TEXT,
    confidence FLOAT,
    source TEXT,
    created_at TIMESTAMP
);

-- Procedural workflows
CREATE TABLE procedural_workflows (
    id UUID PRIMARY KEY,
    name TEXT,
    steps JSONB,
    success_rate FLOAT,
    average_time INT,
    learned BOOLEAN DEFAULT FALSE
);

-- Affective user profile
CREATE TABLE affective_profile (
    user_id UUID PRIMARY KEY,
    preferences JSONB,
    goals TEXT[],
    learning_style TEXT,
    communication_style TEXT,
    risk_tolerance FLOAT
);
\\\

### Indexes for Performance

\\\sql
-- Episodic search
CREATE INDEX idx_episodic_timestamp ON episodic_memories(timestamp DESC);
CREATE INDEX idx_episodic_tags ON episodic_memories USING GIN(tags);

-- Semantic queries
CREATE INDEX idx_semantic_subject ON semantic_facts(subject);
CREATE INDEX idx_semantic_predicate ON semantic_facts(predicate);

-- Affective lookups
CREATE INDEX idx_affective_user ON affective_profile(user_id);
\\\

---

## Retrieval Strategies

### Episodic Retrieval
\\\
1. Semantic similarity search (Qdrant)
2. Temporal filtering (recent first)
3. Tag matching (categorical)
4. Relevance ranking (user interaction signals)
\\\

### Semantic Retrieval
\\\
1. Entity linking (extract mentions)
2. Graph traversal (1-2 hops)
3. Inference (transitivity, inverse relations)
4. Confidence scoring
\\\

### Procedural Retrieval
\\\
1. Task matching (similarity)
2. Sub-task decomposition
3. Success prediction
4. Estimated duration
\\\

---

## Memory Lifecycle

1. **Encoding** - Convert to embeddings, extract entities
2. **Storage** - Write to appropriate database
3. **Consolidation** - Merge, deduplicate, compress
4. **Decay** - Lower relevance for old, unused memories
5. **Retrieval** - Fetch when relevant to current context
6. **Reflection** - Analyze for learning opportunities

