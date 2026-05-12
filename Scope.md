# ContextForge

## Config-Aware Hybrid RAG Research Workbench

ContextForge is an open-source, modular, configurable, research-and-production-ready Hybrid RAG Workbench.

It is not a chatbot, a LangChain demo, or a toy RAG app. It is a retrieval infrastructure platform for building, comparing, debugging, and deploying retrieval pipelines under real-world hardware constraints.

## Tagline

ContextForge is a config-aware hybrid RAG workbench for building, comparing, and deploying production-ready retrieval pipelines.

## System Philosophy

ContextForge is designed as one application with capability-driven behavior.

There are no separate versions such as `v1`, `v2`, `demo app`, or `local app`. Instead, the same application exposes different capabilities depending on configuration, installed dependencies, available hardware, API keys, and deployment profile.

Every major capability can be:

```text
enabled
locked
disabled
experimental
requires_install
requires_api_key
coming_soon
```

The system should feel like:

```text
VSCode for RAG systems
+
Docker for retrieval pipelines
+
Observable AI infrastructure
```

It should not feel like:

```text
a chatbot wrapper
```

## Primary Goals

### Research Goal

Allow users to experiment with:

- retrieval strategies
- chunking algorithms
- embedding models
- sparse retrieval
- dense retrieval
- hybrid fusion methods
- rerankers
- context packing
- LLM generation
- evaluation metrics

### Engineering Goal

Demonstrate production-grade AI infrastructure:

- modular backend architecture
- async APIs
- config-aware capability gating
- observability
- tracing
- hardware-aware deployment
- provider abstraction
- evaluation-first development
- local and hosted deployment support

### Portfolio Goal

Signal:

```text
production AI systems engineer
```

not:

```text
prompt engineer
```

## Target Users

### Beginner Users

Use the hosted demo with restrictions and safe defaults.

### Local GPU Users

Clone the repository and unlock heavier features using local hardware.

### Researchers

Compare retrieval algorithms, chunking methods, embeddings, rerankers, and evaluation metrics.

### AI Engineers

Use ContextForge as a modular RAG experimentation platform.

### Companies

Use ContextForge as an internal retrieval workbench or foundation for production RAG infrastructure.

## Deployment Strategy

### Local Development Machine

The primary development environment is a GPU laptop with approximately:

```text
16GB VRAM
```

Used for:

- development
- testing
- heavier embedding models
- local LLMs
- rerankers
- experimental retrieval strategies
- evaluation jobs

### Hosted Demo Machine

The public demo environment targets approximately:

```text
6GB VRAM
```

Used for:

- restricted public demo
- lightweight inference
- safe upload limits
- selected embedding models
- selected retrieval strategies
- locked heavy capabilities

The hosted demo should clearly state:

```text
This deployment is running in restricted 6GB VRAM demo mode.
Clone the repository and edit config.json to unlock heavier pipelines.
```

## Configuration System

The entire application is capability-driven and controlled through:

```text
config.json
```

The configuration system controls:

- deployment profile
- broad feature gates
- available dropdown options
- selected default algorithms
- algorithm allowlists
- disabled algorithms as `false`
- model restrictions
- registry item visibility
- memory limits
- token limits
- upload limits
- GPU constraints
- CPU constraints
- API provider availability
- feature visibility
- experimental flags
- UI restrictions

### Config Design Principle

`features` should not be only top-level booleans, but the values inside it should still stay simple.

ContextForge needs two related but different layers:

1. Feature gates decide whether a whole system area is available.
2. Option allowlists decide which algorithms, models, providers, and backends appear inside that system area.

For example, the chunking feature may be enabled, but only safe chunkers should be selectable on a small hosted deployment.

```text
chunking.enabled = true
chunking.options.recursive = true
chunking.options.markdown_heading = true
chunking.options.semantic = false
chunking.options.llm_based = false
```

This lets the backend build deployment-safe dropdowns without putting long descriptions or lock reasons inside `config.json`.

### Example Config

```json
{
  "deployment_profile": "hosted_6gb_demo",
  "hardware": {
    "gpu_enabled": true,
    "gpu_vram_gb": 6,
    "cpu_ram_gb": 16
  },
  "ui": {
    "show_locked_options": true,
    "show_requirement_tooltips": true,
    "show_experimental_badges": true
  },
  "limits": {
    "max_upload_mb": 20,
    "max_docs": 50,
    "max_chunks": 5000,
    "max_context_tokens": 4096,
    "max_generation_tokens": 512,
    "max_top_k": 10
  },
  "storage": {
    "base_dir": "data/users",
    "max_chats_per_user": 5,
    "separate_user_storage": true,
    "separate_chat_folders": true
  },
  "features": {
    "ingestion": {
      "enabled": true,
      "default": "markdown",
      "types": {
        "markdown": true,
        "txt": true,
        "pdf": false,
        "docx": false,
        "html": false,
        "github_repo": false,
        "notion": false,
        "confluence": false,
        "youtube_transcript": false
      }
    },
    "document_processing": {
      "enabled": true,
      "cleaning": {
        "whitespace_cleanup": true,
        "markdown_normalization": true,
        "code_block_preservation": true,
        "table_preservation": true,
        "unicode_normalization": true,
        "deduplication": true,
        "metadata_extraction": true
      },
      "max_file_mb": 20
    },
    "chunking": {
      "enabled": true,
      "default": "recursive",
      "options": {
        "fixed_size": true,
        "token": true,
        "sentence": true,
        "sentence_window": true,
        "paragraph": true,
        "markdown_heading": true,
        "recursive": true,
        "sliding_window": true,
        "semantic": false,
        "parent_child": false,
        "small_to_big": false,
        "hierarchical": false,
        "hierarchical_semantic": false,
        "metadata_aware": true,
        "table_aware": false,
        "html_dom": false,
        "ast_code": false,
        "function_class": false,
        "notebook_cell": false,
        "graph": false,
        "proposition_based": false,
        "llm_based": false,
        "adaptive": false,
        "query_aware_dynamic": false,
        "late_chunking": false
      },
      "option_defaults": {
        "recursive": {
          "chunk_size_tokens": 512,
          "chunk_overlap_tokens": 64,
          "preserve_markdown_headings": true,
          "preserve_code_blocks": true
        },
        "sliding_window": {
          "chunk_size_tokens": 512,
          "chunk_overlap_tokens": 128
        }
      }
    },
    "embeddings": {
      "enabled": true,
      "default": "bge-small-en-v1.5",
      "models": {
        "all-MiniLM-L6-v2": true,
        "bge-small-en-v1.5": true,
        "e5-small-v2": true,
        "bge-base": false,
        "e5-base": false,
        "gte-base": false,
        "nomic-embed": false,
        "bge-large": false,
        "e5-large": false,
        "openai-embeddings": false,
        "cohere-embeddings": false,
        "voyage-embeddings": false,
        "jina-embeddings": false
      }
    },
    "vectorstores": {
      "enabled": true,
      "default": "qdrant",
      "options": {
        "qdrant": true,
        "faiss": false,
        "chroma": false,
        "pgvector": false,
        "milvus": false,
        "weaviate": false,
        "elasticsearch": false,
        "opensearch": false
      }
    },
    "sparse_retrieval": {
      "enabled": true,
      "default": "bm25",
      "options": {
        "bm25": true,
        "bm25_plus": false,
        "bm25l": false,
        "tfidf": true,
        "splade": false,
        "bm42": false,
        "elastic_sparse": false,
        "qdrant_sparse_vectors": false
      }
    },
    "fusion": {
      "enabled": true,
      "default": "rrf",
      "options": {
        "weighted": true,
        "rrf": true,
        "comb_sum": false,
        "comb_mnz": false,
        "borda_count": false,
        "distribution_based": false,
        "z_score": false,
        "min_max": false,
        "adaptive_hybrid_weighting": false,
        "query_classifier_based": false,
        "learned_fusion": false,
        "cross_encoder_guided": false
      },
      "option_defaults": {
        "weighted": {
          "dense_weight": 0.7,
          "sparse_weight": 0.3
        },
        "rrf": {
          "k": 60
        }
      }
    },
    "reranking": {
      "enabled": false,
      "default": "none",
      "models": {
        "none": true,
        "cross-encoder-ms-marco-MiniLM": false,
        "bge-reranker-base": false,
        "bge-reranker-large": false,
        "colbert": false,
        "llm_reranking": false,
        "cohere-rerank": false,
        "jina-rerank": false,
        "voyage-rerank": false
      }
    },
    "context_packing": {
      "enabled": true,
      "default": "top_k",
      "options": {
        "top_k": true,
        "score_threshold": true,
        "diversity_aware": false,
        "mmr": false,
        "metadata_grouped": true,
        "section_aware": true,
        "lost_in_middle_mitigation": true,
        "context_compression": false,
        "summary_compression": false,
        "token_budget": true
      }
    },
    "llms": {
      "enabled": true,
      "default_provider": "ollama",
      "default_model": "gemma3:4b",
      "providers": {
        "ollama": true,
        "mock": true,
        "openai_compatible": false,
        "llama_cpp": false,
        "vllm": false,
        "groq": false,
        "openrouter": false,
        "together": false,
        "fireworks": false,
        "anthropic": false,
        "gemini": false
      },
      "models": {
        "gemma3:4b": true,
        "gemma4:e2b-q4": false,
        "gemma4:e4b-q4": false,
        "qwen3:4b": false,
        "phi-mini": false,
        "gemma3:12b-q4": false,
        "llama3:8b-q4": false,
        "mixtral": false,
        "deepseek-large": false
      }
    },
    "streaming": {
      "enabled": true,
      "token_streaming": true,
      "trace_streaming": true
    },
    "evaluation": {
      "enabled": true,
      "metrics": {
        "latency": true,
        "token_usage": true,
        "retrieval_precision": true,
        "recall": false,
        "faithfulness": false,
        "groundedness": false,
        "hallucination_score": false,
        "chunk_relevance": true,
        "ragas": false,
        "deepeval": false,
        "llm_as_judge": false
      }
    },
    "debug_panel": {
      "enabled": true
    }
  }
}
```

### Config Schema Pattern

Every registry-backed feature should use simple booleans for deployment allowlists:

```json
{
  "enabled": true,
  "default": "option_id",
  "options": {
    "option_a": true,
    "option_b": true,
    "option_c": false
  },
  "option_defaults": {
    "option_a": {
      "setting": "value"
    }
  }
}
```

The config file should stay compact and operational. It should answer one main question:

```text
Can this deployment run this option: true or false?
```

Reasons, labels, descriptions, badges, hardware requirements, and tooltips belong in registries and the resolved capabilities endpoint. The backend must enforce the boolean allowlist so users cannot call disabled algorithms directly through the API.

### Deployment Profiles

Supported profiles:

```text
hosted_6gb_demo
local_16gb_gpu
cpu_only
research_mode
enterprise_mode
minimal_mode
offline_mode
```

Each profile should map to default limits, feature states, algorithm availability, model availability, provider availability, and UI behavior.

## Capability System

The capabilities endpoint is one of the most important backend surfaces.

Frontend should not hardcode feature availability. Instead, it should query:

```text
GET /capabilities
```

The response determines:

- enabled options
- locked options
- disabled options
- requirements
- tooltips
- badges
- model visibility
- dropdown contents
- selected defaults
- per-option configuration controls
- deployment restrictions

### Capability Statuses

```text
enabled
locked
disabled
experimental
requires_install
requires_api_key
coming_soon
```

### Example Capability Item

```json
{
  "id": "semantic_chunking",
  "label": "Semantic Chunking",
  "category": "chunking",
  "status": "locked",
  "description": "Embedding-aware semantic chunking.",
  "requirements": {
    "min_ram_gb": 8,
    "requires_embedding_model": true
  },
  "tags": ["research", "expensive", "high-quality"]
}
```

### Example Capability Response

```json
{
  "chunking": {
    "status": "enabled",
    "default": "recursive",
    "options": [
      {
        "id": "recursive",
        "label": "Recursive Chunking",
        "status": "enabled",
        "config": {
          "chunk_size_tokens": 512,
          "chunk_overlap_tokens": 64
        }
      },
      {
        "id": "semantic",
        "label": "Semantic Chunking",
        "status": "locked",
        "reason": "Requires embedding-based boundary detection and more memory."
      }
    ]
  },
  "llms": {
    "status": "enabled",
    "default_provider": "ollama",
    "default_model": "gemma3:4b",
    "models": [
      {
        "id": "gemma3:4b",
        "status": "enabled"
      },
      {
        "id": "gemma3:12b-q4",
        "status": "locked",
        "reason": "Requires approximately 8GB+ VRAM."
      }
    ]
  }
}
```

## Registry Architecture

The application should never hardcode user-facing algorithm or provider options directly in components.

All configurable capabilities should be declared through registries.

Registries define everything the application knows how to support. `config.json` defines what the current deployment is allowed to expose and run.

This separation is important:

```text
Registry = complete catalog of implemented/planned options
Config = deployment-specific allowlist, defaults, limits, and locks
Capabilities endpoint = resolved registry + config + hardware + installed dependencies
```

For example, `Semantic Chunking` can exist in `ChunkerRegistry`, but remain locked in `hosted_6gb_demo` because the current deployment should only expose cheaper chunking choices.

### Core Registries

```text
ChunkerRegistry
EmbeddingRegistry
VectorStoreRegistry
SparseRetrieverRegistry
FusionRegistry
RerankerRegistry
LLMRegistry
ContextPackerRegistry
RetrieverStrategyRegistry
ProviderRegistry
```

### Registry Item Fields

Each registry item should include:

- `id`
- `label`
- `category`
- `status`
- `description`
- `requirements`
- `tags`
- `default_config`
- `profile_overrides`
- `estimated_resource_usage`
- `provider`
- `implementation_path`

## High-Level Pipeline

Every user request should be visually traceable.

```text
User Query
↓
Query Processing
↓
Sparse Retrieval
+
Dense Retrieval
↓
Hybrid Fusion
↓
Reranking
↓
Context Packing
↓
LLM Generation
↓
Answer + Citations
```

The UI should expose every stage, including scores, latency, selected chunks, rejected chunks, prompts, context windows, and generated citations.

## Query Understanding System

The query understanding layer detects user intent before retrieval.

### Query Types

```text
factual
comparative
summarization
timeline
code search
reasoning
multi-hop
definition
exploration
```

### Features

- query classification
- intent detection
- query difficulty estimation
- retrieval depth selection
- dynamic routing
- fusion strategy selection
- reranker selection

Example:

```text
"compare BM25 and dense retrieval"
```

should trigger comparative retrieval behavior.

## Query Processing

Query processing improves retrieval quality before search.

Supported modes:

- raw query
- query cleaning
- stopword handling
- query expansion
- query rewriting
- multi-query retrieval
- HyDE
- step-back querying

### Query Rewriting Example

```text
"What changed in retrieval systems?"
→
"Compare recent retrieval architecture improvements"
```

### Multi-Query Example

```text
semantic query
keyword query
broader query
specific query
```

## Query Routing System

The routing layer maps queries to retrieval pipelines.

Example:

```text
code query
→ AST chunking
→ code embeddings
→ code reranker
```

Routing modes:

- rule-based routing
- classifier routing
- LLM routing
- hybrid routing

## Document Processing Pipeline

Document ingestion should be async, traceable, and observable.

### Stages

```text
load
clean
normalize
deduplicate
extract metadata
chunk
embed
index
```

### Cleaning Features

- whitespace cleanup
- markdown normalization
- code block preservation
- table preservation
- unicode normalization
- duplicate removal
- metadata extraction

## Supported Ingestion Types

### Initial

```text
Markdown
TXT
PDF
DOCX
```

### Planned

```text
HTML
GitHub repositories
Notion
Confluence
YouTube transcripts
```

## Metadata System

Metadata enables filtering, grouping, ranking, citations, and advanced retrieval.

Example metadata:

```json
{
  "source": "retrieval.md",
  "section": "fusion",
  "subsection": "rrf",
  "author": "user",
  "created_at": "2026",
  "language": "en",
  "tags": ["rag", "retrieval"],
  "doc_type": "markdown"
}
```

Metadata filtering examples:

- retrieve only architecture docs
- retrieve only code files
- retrieve only docs after 2025
- retrieve only trusted sources
- retrieve only selected collections

## Chunking System

Chunking divides documents into retrievable units. Chunk quality strongly affects retrieval precision, answer quality, citation quality, and hallucination rate.

### Supported Chunking Strategies

```text
Fixed-size chunking
Token-based chunking
Sentence chunking
Sentence-window chunking
Paragraph chunking
Markdown heading chunking
Recursive chunking
Sliding-window chunking
Semantic chunking
Parent-child chunking
Small-to-big chunking
Hierarchical chunking
Hierarchical semantic chunking
Metadata-aware chunking
Table-aware chunking
HTML DOM chunking
AST/code chunking
Function/class chunking
Notebook cell chunking
Graph chunking
Proposition-based chunking
LLM-based chunking
Adaptive chunking
Query-aware dynamic chunking
Late chunking
```

### Important Chunking Modes

Fixed-size chunking is simple, fast, and predictable, but can break semantic meaning.

Token-based chunking uses tokenizer-aware boundaries and is safer than raw character splitting.

Sentence and paragraph chunking preserve semantic units and work well for clean prose.

Markdown heading chunking is critical for technical documentation because it preserves document hierarchy.

Recursive chunking is a strong general-purpose default because it can split by heading, paragraph, sentence, and token limits.

Sliding-window chunking adds overlap to preserve continuity.

Semantic chunking uses embeddings to detect topic shifts. It is higher quality but more expensive.

Parent-child and small-to-big chunking retrieve precise child chunks and expand to richer parent context during packing.

AST/code chunking parses code structure and chunks by functions, classes, methods, imports, and symbols.

## Embedding System

Embeddings convert text into vectors that represent semantic meaning.

Used for:

- semantic search
- dense retrieval
- reranking support
- clustering
- similarity search
- semantic cache lookup

### Lightweight Models

```text
all-MiniLM-L6-v2
bge-small-en-v1.5
e5-small-v2
```

Recommended hosted-demo default:

```text
bge-small-en-v1.5
```

### Medium Models

```text
bge-base
e5-base
gte-base
nomic-embed
```

### Heavy Models

```text
bge-large
e5-large
Jina embeddings
Voyage embeddings
```

### API Embeddings

```text
OpenAI embeddings
Cohere embeddings
Voyage embeddings
Jina embeddings
```

API embeddings should be marked `requires_api_key`.

## Sparse Retrieval System

Sparse retrieval uses keyword and token matching.

It is excellent for:

- exact terms
- acronyms
- code symbols
- rare terminology
- product names
- IDs
- file paths

### Supported Sparse Retrievers

```text
BM25
BM25+
BM25L
TF-IDF
SPLADE
BM42
Elastic sparse retrieval
Qdrant sparse vectors
```

BM25 should be the default sparse baseline.

## Dense Retrieval System

Dense retrieval uses vector similarity to retrieve semantically related content.

Strengths:

- semantic understanding
- concept matching
- paraphrase handling

Weaknesses:

- weaker exact term matching
- acronym failures
- rare keyword failures
- code symbol failures

## Hybrid Retrieval System

Hybrid retrieval combines sparse and dense retrieval and should be the default production-oriented retrieval strategy.

### Supported Fusion Algorithms

```text
Weighted fusion
RRF
CombSUM
CombMNZ
Borda Count
Distribution-based fusion
Z-score normalization fusion
Min-max normalization fusion
Adaptive hybrid weighting
Query-classifier-based fusion
Learned fusion
Cross-encoder-guided fusion
```

### Recommended Defaults

For simple local and hosted use:

```text
Weighted fusion
RRF
```

Weighted fusion is simple, fast, and controllable.

RRF combines rankings instead of raw scores and is a strong default for hybrid retrieval.

## Reranking System

Reranking is the second-stage refinement step after retrieval.

Initial retrieval gets candidates. Reranking reorders candidates with a more expensive but more accurate model.

### Supported Rerankers

```text
None
cross-encoder/ms-marco-MiniLM
bge-reranker-base
bge-reranker-large
ColBERT
LLM reranking
Cohere rerank API
Jina reranker API
Voyage reranker API
```

### Recommended Defaults

Hosted demo:

```text
None or cross-encoder/ms-marco-MiniLM
```

Local 16GB GPU:

```text
bge-reranker-base
```

Heavy or research profile:

```text
bge-reranker-large
ColBERT
LLM reranking
```

## Context Engineering

Context engineering builds the final context sent to the LLM.

It is responsible for relevance, citation quality, source grouping, token budget usage, and hallucination reduction.

### Supported Context Packing Strategies

```text
Top-k packing
Score-threshold packing
Diversity-aware packing
MMR packing
Metadata-grouped packing
Section-aware packing
Lost-in-the-middle mitigation
Context compression
Summary compression
Token-budget optimizer
```

The token-budget optimizer is mandatory for production behavior.

## LLM Generation System

The LLM generation layer produces grounded answers using retrieved context.

### Supported Runtimes

```text
Ollama
llama.cpp
vLLM
OpenAI-compatible APIs
Groq
OpenRouter
Together
Fireworks
Anthropic
Google Gemini API
Mock provider
```

### Primary Local Runtime

```text
Ollama
```

Ollama setup:

```bash
ollama pull gemma3:4b
ollama serve
```

Backend communicates with:

```text
http://localhost:11434
```

### Provider Adapters

```text
OllamaProvider
OpenAICompatibleProvider
LlamaCppProvider
VLLMProvider
MockProvider
```

### Safe Local Models

```text
Gemma 4 E2B Q4
Gemma 4 E4B Q4
Gemma 3 4B Q4
Qwen 3B/4B
Phi Mini
```

### Heavy Models

```text
Gemma 12B+
Llama 8B+
Mixtral
DeepSeek large models
```

Heavy models should be visible but locked in hosted deployments.

## Retrieval Failure Handling

The system should detect and recover from weak retrieval.

### Features

- low confidence detection
- dense-to-sparse fallback
- sparse-to-dense fallback
- alternate query generation
- empty retrieval recovery
- reranker confidence checks
- hallucination prevention
- unsupported answer blocking

Example:

```text
dense retrieval failed
→ fallback to BM25
```

## Safety System

ContextForge should treat retrieved text as untrusted input.

### Features

- prompt injection detection
- context sanitization
- dangerous instruction filtering
- output filtering
- source trust scoring
- citation trust indicators

## Evaluation System

ContextForge should be evaluation-first.

Without evaluations, users cannot know whether retrieval is improving.

### Metrics

```text
Faithfulness
Groundedness
Retrieval precision
Recall
Hallucination score
Latency
Token usage
Chunk relevance
```

### Latency Breakdown

Track:

- query processing time
- embedding time
- sparse retrieval time
- dense retrieval time
- fusion time
- reranking time
- context packing time
- generation time
- total request time

### Token Usage

Track:

- prompt tokens
- completion tokens
- retrieved context tokens
- final packed context tokens
- discarded context tokens

### Planned Evaluation Integrations

```text
RAGAS
DeepEval
Phoenix
Langfuse
LLM-as-judge systems
```

## Benchmarking System

Users should be able to compare pipelines over benchmark datasets.

### Benchmarked Dimensions

- retrieval quality
- faithfulness
- hallucination rate
- latency
- token usage
- cost
- citation quality

### Dataset Support

```text
custom datasets
RAG benchmarks
user-uploaded eval sets
```

## Observability System

Every request should produce a trace.

### Supported Observability Features

```text
Trace visualization
Retrieval inspector
Latency metrics
Prompt inspection
Chunk inspection
Fusion score analysis
Context viewer
```

### Future Observability Integrations

```text
OpenTelemetry
Langfuse
Phoenix
Weights & Biases
```

## Retrieval Inspector

The inspector should display:

```text
retrieved chunks
metadata
source path
heading
chunk size
BM25 score
vector score
fusion score
reranker score
latency
selected/rejected state
```

## Chunk Viewer

Each chunk should show:

```text
document path
heading
metadata
token count
score
matched text highlights
```

## Algorithm Comparison Mode

Users should compare pipelines side-by-side.

Initial comparison modes:

```text
BM25 only
Vector only
Hybrid weighted
Hybrid RRF
```

Comparison output should include:

- retrieved chunks
- score breakdowns
- overlap analysis
- latency
- final packed context
- answer quality
- citations

## Streaming System

Supported streaming features:

- token streaming
- progressive retrieval streaming
- trace streaming
- live pipeline execution updates

The UI should be able to show retrieval progress before generation completes.

## Caching System

Caching is critical for latency, cost reduction, and scalability.

### Cache Types

- embedding cache
- retrieval cache
- prompt cache
- generation cache
- semantic cache

The cache system should be configurable per deployment profile.

## Memory Systems

Planned memory systems:

```text
Session memory
Conversation memory
Semantic memory
Episodic memory
Long-term memory
Memory scoring
Memory decay
Memory compression
```

Memory features should start disabled or experimental until core retrieval is stable.

## User Storage System

Each user should have isolated storage.

Each chat should have its own folder inside that user's storage area. This keeps uploaded documents, generated chunks, vector collection references, traces, configs, and exports separated per chat.

### Chat Limit

Each user can have a maximum of:

```text
5 chats
```

When the user reaches 5 chats, the UI should prevent creating another chat unless an existing chat is deleted or archived.

### Folder Layout

Example local storage layout:

```text
data/
  users/
    {user_id}/
      profile.json
      chats/
        {chat_id}/
          chat.json
          config.snapshot.json
          uploads/
          processed/
          chunks/
          indexes/
          traces/
          exports/
```

### Per-Chat Isolation

Each chat owns:

- uploaded source files
- cleaned documents
- chunk outputs
- retrieval traces
- evaluation runs
- generated exports
- config snapshot used for that chat
- vector collection or collection namespace

This makes chats reproducible and prevents one chat's uploaded knowledge base from leaking into another chat.

### Storage Rules

- Users cannot access another user's folders.
- Chats cannot access another chat's documents unless cross-chat retrieval is explicitly added later.
- Deleting a chat should delete or archive that chat folder and its vector collection.
- Each chat should keep a config snapshot so old traces remain reproducible even if global `config.json` changes later.

## Collection Management

ContextForge should support multiple knowledge bases.

### Features

```text
multiple knowledge bases
collection switching
cross-collection retrieval
collection merging
isolated vector collections
```

## Multi-Tenancy Architecture

Future enterprise support should allow:

```text
multiple users
multiple projects
isolated vector collections
workspace separation
```

Multi-tenancy is not required for the first hosted demo, but the storage and API design should avoid blocking it.

## Code RAG System

Code RAG requires specialized document processing and retrieval.

### Features

- AST parsing
- symbol extraction
- function chunking
- class chunking
- dependency graph extraction
- repo-aware retrieval
- code-symbol retrieval

Tracked symbols:

```text
functions
classes
imports
variables
methods
modules
```

## Document Linking System

The document linking layer supports future GraphRAG workflows.

### Features

- semantic linking
- citation graph
- related chunk graph
- source relationship graph
- knowledge graph foundation

## Agentic Retrieval Foundation

ContextForge is not a full agent framework, but the architecture should support future agentic retrieval.

Supported foundations:

```text
recursive retrieval
tool use
planner-executor patterns
multi-hop retrieval
```

## Tool System

Future tools:

```text
calculator
web search
python execution
SQL querying
code execution
document editing
```

Tool execution should be explicitly gated by config and safety policy.

## Export System

Users should be able to export:

- answers
- citations
- retrieval traces
- evaluation reports
- benchmark results
- config snapshots

Supported formats:

```text
markdown
PDF
JSON
CSV
```

## Hardware Detection System

The backend should detect:

```text
GPU
VRAM
RAM
CUDA
CPU cores
installed runtimes
installed models
```

Used to:

- auto-lock heavy features
- recommend models
- adjust defaults
- estimate memory usage
- warn before loading large models

## Model Management System

### Features

- installed Ollama model detection
- model pull suggestions
- VRAM estimation
- provider health checks
- model compatibility checks

Example suggestion:

```text
Gemma 4 E4B is not installed.
Run: ollama pull gemma4:e4b
```

## Task Queue System

Heavy tasks should run asynchronously.

### Task Types

```text
embedding generation
document ingestion
reranking
evaluation jobs
benchmark jobs
index rebuilds
```

### Future Queue Tools

```text
Celery
RQ
Redis queues
```

## Database System

### Default

```text
SQLite
```

Used for:

- metadata
- documents
- chunks
- traces
- configs
- evaluation runs

### Future

```text
PostgreSQL
Redis
```

PostgreSQL is for production metadata storage. Redis is for queues and caching.

## Vector Databases

### Supported

```text
Qdrant
FAISS
Chroma
pgvector
Milvus
Weaviate
Elasticsearch
OpenSearch
```

### Hosted Demo Enabled

```text
Qdrant
```

## Search Modes

```text
Standard Search
Deep Search
Research Mode
Fast Mode
Explainability Mode
```

Standard Search uses balanced defaults.

Deep Search increases retrieval depth and may use reranking.

Research Mode enables comparison, recursive retrieval, and expanded traces.

Fast Mode prioritizes latency and may disable reranking.

Explainability Mode prioritizes trace visibility and score inspection.

## Plugin System

The architecture should support future extensions.

### Plugin Types

```text
custom chunkers
custom retrievers
custom rerankers
custom vector DBs
custom providers
custom evaluators
custom context packers
```

Plugins should register capabilities through the same registry system as built-in modules.

## Frontend Stack

### Core

```text
React
Vite
TailwindCSS
TypeScript
```

### Libraries

```text
shadcn/ui
Radix UI
Lucide Icons
Zustand
TanStack Query
React Flow
D3.js
Recharts
Monaco Editor
```

## Frontend Structure

```text
frontend/src/
  pages/
  components/
  layouts/
  hooks/
  services/
  stores/
  lib/
  styles/
  types/
```

## Frontend Pages

```text
/
Workbench
Inspector
Config
Evaluations
Manual
Docs
```

### Landing Hero

Hero content:

```text
ContextForge
The Config-Aware Hybrid RAG Workbench
```

Hero buttons:

```text
View GitHub
Try Demo
Read Manual
Start Local Setup
```

### Workbench

Main interactive RAG pipeline interface:

- query input
- pipeline selector
- retrieval controls
- model selector
- context settings
- generated answer
- citations
- live trace panel

### Inspector

Detailed trace and retrieval debugging:

- chunk table
- score breakdown
- latency waterfall
- prompt viewer
- context viewer
- selected versus rejected chunks

### Config

Visual config editing:

- toggle pipelines
- adjust limits
- switch profiles
- edit providers
- configure API keys
- inspect locked capabilities

### Evaluations

Evaluation and benchmarking:

- dataset upload
- benchmark runs
- metric charts
- pipeline comparison
- export reports

## Backend Stack

### Core

```text
FastAPI
Python
Pydantic
Uvicorn
```

### AI Libraries

```text
sentence-transformers
transformers
torch
rank-bm25
numpy
scikit-learn
```

### Infrastructure

```text
Docker
Docker Compose
Qdrant
SQLite
Redis
```

Redis is future-facing for queues and caching.

## Backend Structure

```text
backend/app/
  api/
  core/
  registries/
  ingestion/
  chunking/
  embeddings/
  vectorstores/
  sparse/
  retrieval/
  reranking/
  fusion/
  generation/
  context/
  evaluation/
  observability/
  storage/
  providers/
  schemas/
  services/
  utils/
```

## API Architecture

Principles:

```text
modular
provider-based
async-first
streaming-capable
stateless APIs
config-aware
traceable
```

### Core Endpoints

```text
GET /health
GET /capabilities
GET /config

POST /ingest
POST /retrieve
POST /ask
POST /compare

GET /traces/{id}
GET /models
GET /embeddings
GET /retrievers
```

### Future Endpoints

```text
POST /evaluate
POST /benchmarks
GET /benchmarks/{id}
GET /collections
POST /collections
GET /providers
GET /hardware
GET /tasks/{id}
```

## Docker Strategy

### Containers

```text
frontend
backend
qdrant
optional ollama
```

### Local Setup

```bash
git clone https://github.com/yourname/contextforge.git
cd contextforge
cp config.example.json config.json
docker compose up --build
```

## Local Setup Modes

### Mode A: Docker + OpenAI-Compatible API

Easiest setup. Uses Dockerized services and an external LLM API.

### Mode B: Ollama

Local quantized LLMs through Ollama.

### Mode C: Research GPU

Local GPU setup with heavier models, rerankers, larger embeddings, and optional vLLM.

## Deployment Targets

### Frontend

```text
Vercel
Netlify
Cloudflare Pages
```

### Backend

```text
Railway
Render
RunPod
VPS
Docker deployment
```

### Vector Database

```text
Qdrant Cloud
Dockerized Qdrant
```

## Suggested Initial Build Phases

### Phase 1: Core Skeleton

- FastAPI backend
- React frontend
- config loader
- capability endpoint
- registry structure
- health endpoint
- mock provider
- basic workbench UI

### Phase 2: Minimal RAG

- Markdown and TXT ingestion
- recursive or markdown chunking
- bge-small or MiniLM embeddings
- Qdrant vector store
- BM25 sparse retriever
- weighted hybrid fusion
- top-k context packing
- Ollama or mock generation
- basic traces

### Phase 3: Inspection and Comparison

- retrieval inspector
- score breakdowns
- BM25 versus vector versus hybrid comparison
- trace viewer
- latency metrics
- config UI

### Phase 4: Evaluation

- evaluation datasets
- retrieval precision
- recall
- groundedness
- latency tracking
- exportable reports

### Phase 5: Advanced Research Features

- semantic chunking
- parent-child retrieval
- rerankers
- RRF
- multi-query retrieval
- HyDE
- context compression
- advanced observability integrations

## Final Architecture Summary

ContextForge is a modular, configurable, visually explainable, research-and-production-ready hybrid RAG operating system.

It is built around one core idea:

```text
The retrieval pipeline should be configurable, inspectable, comparable, and deployable.
```

The application should visually expose the entire retrieval process from query processing to answer generation, while the backend remains modular enough to support new chunkers, retrievers, embedding models, rerankers, providers, vector stores, evaluators, and deployment profiles.
