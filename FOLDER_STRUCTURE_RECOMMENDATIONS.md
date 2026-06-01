# RECOMMENDED FOLDER STRUCTURE - COGNITIVE OS

## Current Structure Analysis

Current is basic:
\\\
services/gateway/src/
  ├── main.py (all logic here)
  ├── models.py (all ORM)
  ├── auth.py
  ├── llm.py
  ├── storage.py
  └── capabilities.py
\\\

**Problems:**
- 13 features mixed in main.py
- No clear cognitive layers
- Hard to extend independently
- Difficult to test

---

## Recommended Structure: LAYERED COGNITIVE ARCHITECTURE

\\\
services/gateway/
├── src/
│   ├── api/                           # API layer
│   │   ├── __init__.py
│   │   ├── routes.py                  # FastAPI routes
│   │   ├── middleware.py              # Authentication, logging
│   │   ├── schemas.py                 # Request/response validators
│   │   └── errors.py                  # Error handlers
│   │
│   ├── perception/                    # INPUT LAYER
│   │   ├── __init__.py
│   │   ├── text_processor.py          # Intent extraction, entity linking
│   │   ├── speech_service.py          # Whisper integration (Phase 5)
│   │   ├── vision_service.py          # YOLOv8, CLIP (Phase 5)
│   │   └── multimodal_fusion.py       # Combine audio/vision/text
│   │
│   ├── memory/                        # MEMORY LAYER
│   │   ├── __init__.py
│   │   ├── episodic.py                # Event memories (SQL + vector)
│   │   ├── semantic.py                # Facts and relationships
│   │   ├── procedural.py              # Workflows and skills
│   │   ├── working.py                 # Current conversation context
│   │   ├── storage.py                 # SQL repository
│   │   ├── embeddings.py              # OpenAI embeddings (Phase 1)
│   │   ├── vector_memory.py           # Qdrant integration (Phase 1)
│   │   ├── consolidation.py           # Merge, deduplicate (Phase 1)
│   │   └── retrieval.py               # Search strategies
│   │
│   ├── knowledge/                     # KNOWLEDGE LAYER
│   │   ├── __init__.py
│   │   ├── graph.py                   # Neo4j integration (Phase 2)
│   │   ├── entities.py                # Entity management
│   │   ├── relationships.py           # Relationship management
│   │   ├── inference.py               # Transitive, causal reasoning
│   │   ├── world_state.py             # Current state tracking
│   │   └── queries.py                 # Cypher query templates
│   │
│   ├── reasoning/                     # REASONING LAYER
│   │   ├── __init__.py
│   │   ├── constraint_solver.py       # CSP solver (Phase 3)
│   │   ├── decision_engine.py         # Decision making
│   │   ├── confidence.py              # Confidence scoring
│   │   └── uncertainty.py             # Uncertainty handling
│   │
│   ├── planning/                      # PLANNING LAYER
│   │   ├── __init__.py
│   │   ├── htn_planner.py             # HTN decomposition (Phase 3)
│   │   ├── task_hierarchy.py          # Task definitions
│   │   ├── methods.py                 # Decomposition methods
│   │   ├── scheduler.py               # Execution scheduling
│   │   └── replanner.py               # Handle failures
│   │
│   ├── agents/                        # AGENT LAYER
│   │   ├── __init__.py
│   │   ├── base_agent.py              # Abstract agent
│   │   ├── coordinator.py             # Route to agents
│   │   ├── planner_agent.py           # Goal decomposition
│   │   ├── research_agent.py          # Knowledge search
│   │   ├── coder_agent.py             # Code analysis
│   │   ├── reasoner_agent.py          # Inference
│   │   ├── memory_agent.py            # Memory management
│   │   ├── voice_agent.py             # Speech handling
│   │   ├── vision_agent.py            # Image handling
│   │   ├── reflection_agent.py        # Learning (Phase 4)
│   │   └── router.py                  # Intelligent routing
│   │
│   ├── learning/                      # LEARNING LAYER (Phase 4)
│   │   ├── __init__.py
│   │   ├── feedback_processor.py      # Process feedback
│   │   ├── rl_agent.py                # Reinforcement learning
│   │   ├── active_learning.py         # Query generation
│   │   ├── transfer_learning.py       # Cross-domain knowledge
│   │   └── curriculum.py              # Progressive learning
│   │
│   ├── reflection/                    # REFLECTION LAYER
│   │   ├── __init__.py
│   │   ├── error_analyzer.py          # Root cause analysis
│   │   ├── confidence_calibrator.py   # Calibration
│   │   ├── strategy_optimizer.py      # Learn better strategies
│   │   └── insight_extractor.py       # Lesson capture
│   │
│   ├── execution/                     # EXECUTION LAYER
│   │   ├── __init__.py
│   │   ├── executor.py                # Plan execution
│   │   ├── tool_manager.py            # Tool/API management
│   │   ├── error_handler.py           # Recovery logic
│   │   └── audit.py                   # Action logging
│   │
│   ├── connectors/                    # INTEGRATION LAYER
│   │   ├── __init__.py
│   │   ├── base.py                    # Abstract connector
│   │   ├── jira.py                    # JIRA API (Phase 6)
│   │   ├── salesforce.py              # Salesforce API (Phase 6)
│   │   ├── github.py                  # GitHub API (Phase 6)
│   │   ├── gmail.py                   # Email (Phase 6)
│   │   ├── slack.py                   # Slack (Phase 6)
│   │   ├── notion.py                  # Notion (Phase 6)
│   │   └── robotics.py                # Robot control (Phase 6)
│   │
│   ├── config/                        # CONFIGURATION
│   │   ├── __init__.py
│   │   ├── settings.py                # Env vars
│   │   ├── database.py                # DB connection
│   │   ├── logging.py                 # Logging config
│   │   └── features.py                # Feature flags
│   │
│   ├── models.py                      # SQLAlchemy ORM (keep as-is)
│   ├── schemas.py                     # Pydantic schemas (move to api/)
│   └── main.py                        # Entry point (much simpler now)
│
├── tests/
│   ├── unit/
│   │   ├── test_memory.py
│   │   ├── test_reasoning.py
│   │   ├── test_planning.py
│   │   ├── test_learning.py
│   │   └── test_agents.py
│   ├── integration/
│   │   ├── test_memory_knowledge.py
│   │   ├── test_planning_execution.py
│   │   └── test_connectors.py
│   └── e2e/
│       ├── test_full_conversation.py
│       ├── test_learning_feedback.py
│       └── test_embodied_execution.py
│
├── migrations/
│   ├── add_embeddings.py            # Phase 1
│   ├── add_graph_tables.py          # Phase 2
│   └── add_learning_tables.py       # Phase 4
│
└── docker/
    ├── Dockerfile
    └── requirements.txt

apps/web/
├── src/
│   ├── components/
│   │   ├── Chat.tsx
│   │   ├── memory/               # NEW
│   │   │   ├── MemoryBrowser.tsx
│   │   │   └── MemoryViewer.tsx
│   │   ├── knowledge/             # NEW
│   │   │   ├── GraphViewer.tsx
│   │   │   └── EntitySearch.tsx
│   │   ├── learning/              # NEW
│   │   │   ├── LearningDashboard.tsx
│   │   │   └── FeedbackForm.tsx
│   │   └── ui/
│   │       └── ...existing...
│   ├── hooks/
│   │   ├── useChat.ts
│   │   ├── useMemory.ts           # NEW
│   │   ├── useKnowledge.ts        # NEW
│   │   └── useLearning.ts         # NEW
│   ├── store.ts
│   ├── api.ts
│   └── App.tsx
└── ...

\\\

---

## Migration Path

### Week 1-2: Prepare Structure
- Create folder hierarchy
- Move existing code without changes
- Ensure all imports still work

### Week 3: Implement Phase 1
- Create memory/ modules
- Create embeddings.py, vector_memory.py
- Update main.py to use new modules

### Week 4: Implement Phase 2
- Create knowledge/ modules
- Create graph.py, inference.py
- Add graph visualization to UI

### Ongoing
- Each phase adds its layer
- Previous layers remain untouched
- Clean separation of concerns

---

## Benefits

✅ **Modularity** - Each layer independent
✅ **Extensibility** - Easy to add capabilities
✅ **Testability** - Clear unit test boundaries
✅ **Scalability** - Can deploy layers separately
✅ **Clarity** - Cognitive architecture obvious
✅ **Maintainability** - Clear responsibilities

