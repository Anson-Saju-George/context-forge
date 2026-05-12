QUESTIONS = [
  (
    "high_level_comparison",
    """
Give me a complete high-level comparison of all uploaded documents.

Explain:
- what each document is about
- whether it is research-focused, implementation-focused, or operational
- the main problems each document tries to solve
- the core concepts introduced in each document
- how the documents relate to modern AI systems and infrastructure

Compare the papers conceptually and explain how they connect together.
""",
  ),
  (
    "technical_extraction",
    """
Extract the most important technical concepts, architectures, algorithms, and workflows from all uploaded documents.

Include:
- transformer architecture
- retrieval-augmented generation pipelines
- Kubernetes orchestration concepts
- Llama 2 training/alignment ideas
- scaling, inference, deployment, or distributed system concepts

Explain which concepts appear across multiple documents and how they evolved.
""",
  ),
  (
    "learning_roadmap",
    """
Create a practical learning roadmap using all uploaded documents.

Explain:
- what order I should study the documents in
- what beginner, intermediate, and advanced concepts appear
- what prerequisites I need before reading each document
- which documents are theoretical vs implementation-heavy
- what projects or systems I should build after each stage

Design the roadmap for someone who wants to build production-grade AI systems.
""",
  ),
  (
    "implementation_operational_comparison",
    """
Compare the implementation and operational ideas across all uploaded documents.

Explain:
- how Kubernetes infrastructure relates to modern AI systems
- how RAG systems interact with transformer-based models
- how Llama 2 relates to the original transformer architecture
- where deployment, retrieval, scaling, memory, inference, and orchestration appear across the documents

Identify overlapping concepts, complementary ideas, and important differences.
""",
  ),
  (
    "limitations_tradeoffs_bottlenecks",
    """
Identify the most important limitations, tradeoffs, bottlenecks, and unresolved problems discussed or implied across all uploaded documents.

Explain:
- limitations of transformer architectures
- scaling and inference bottlenecks
- retrieval vs parametric memory tradeoffs
- operational challenges in deploying AI systems on Kubernetes
- alignment and safety limitations in Llama-style models
- weaknesses or risks in RAG pipelines

For each issue:
- explain which document discusses or implies it
- describe the technical cause of the limitation
- explain how later systems or papers attempt to address it
- identify which problems still remain unresolved

Prioritize concrete mechanisms, architectures, and operational concerns over high-level summaries.
""",
  ),
  (
    "production_ai_stack",
    """
Compare all uploaded documents as parts of a modern production AI system stack.

For each document:
- explain what problem it solves
- identify whether it is research-focused, implementation-focused, or operational
- extract the most important architectures, algorithms, mechanisms, and workflows
- identify the core technical concepts introduced

Then explain how the documents connect together across the full AI lifecycle:
- transformer architecture
- foundation model training and alignment
- retrieval-augmented generation
- deployment and orchestration infrastructure
- scaling, inference, memory, retrieval, and operational concerns

Prioritize:
- exact technical mechanisms
- concrete architectural components
- operational details
- evidence-grounded comparisons

Avoid generic summaries when specific mechanisms are available.
""",
  ),
]


QUESTION_GROUPS = {
  "set": QUESTIONS[:5],
  "stack": QUESTIONS[5:],
  "all": QUESTIONS,
}


VERSION_BRIEFINGS = {
  "v0": {
    "label": "V0 Similarity Toy",
    "purpose": "Minimal baseline used to show how beginner RAG behaves before real retrieval architecture.",
    "retrieval": ["token-overlap cosine-style similarity", "single-stage retrieval", "top-k chunks only"],
    "ranking": ["single score sort", "no document balancing", "no mechanism-aware reranking"],
    "context": ["direct chunk packing", "no parent expansion", "no MMR"],
    "answering": ["same backend answer layer after retrieval", "citations from similarity chunks"],
    "strengths": ["simple baseline", "clear failure-mode comparison point"],
    "limits": ["weak broad synthesis", "weak mechanism extraction", "right-topic/wrong-evidence risk"],
    "files": ["backend/pipeline/retrieval_v0.py"],
  },
  "v1": {
    "label": "V1 Sparse Foundation",
    "purpose": "First serious local retrieval foundation.",
    "retrieval": ["BM25 sparse retrieval", "hierarchical chunks", "dynamic top-k", "basic intent routing"],
    "ranking": ["specificity reranking", "query/section boosts", "technical-term extraction"],
    "context": ["parent/section expansion", "citations and telemetry"],
    "answering": ["deterministic extraction tables", "Ollama-only non-deterministic generation"],
    "strengths": ["better exact-term recall", "usable cited baseline"],
    "limits": ["weaker broad synthesis", "no formal benchmark gates", "no frozen latency report"],
    "files": ["backend/pipeline/retrieval_v1.py", "backend/pipeline/generation_v1.py", "backend/pipeline/ingestion_v1.py"],
  },
  "v2": {
    "label": "V2 Routed Retrieval",
    "purpose": "First stable benchmarkable RAG milestone.",
    "retrieval": ["general/synthesis/extraction routing", "document-balanced synthesis", "BM25 plus technical-density candidates"],
    "ranking": ["specificity-biased rerank", "concrete mechanism ranking", "operational mechanism scoring"],
    "context": ["compressed evidence chunks", "per-document evidence selection"],
    "answering": ["deterministic synthesis", "deterministic mechanism extraction"],
    "strengths": ["document-level matrices", "better all-document extraction", "repeatable benchmark script"],
    "limits": ["roughly 6-8s per benchmark query", "BM25 stats recomputed per query"],
    "files": ["backend/pipeline/retrieval_v2.py", "backend/pipeline/generation_v2.py", "backend/pipeline/ingestion_v2.py"],
  },
  "v3": {
    "label": "V3 Benchmark Baseline",
    "purpose": "Benchmark-focused production-style local RAG baseline.",
    "retrieval": ["cached BM25 stats", "cached chunk features", "forced document coverage", "document-balanced synthesis"],
    "ranking": ["specificity reranking", "mechanism/operational boosts", "noisy-section penalties", "MMR-style diversity"],
    "context": ["parent/sibling expansion", "source-balanced synthesis", "evidence-only term use"],
    "answering": ["deterministic benchmark templates", "quality gates and reports"],
    "strengths": ["warmed synthesis about 160-170ms", "algorithm extraction about 540ms", "stronger source coverage"],
    "limits": ["cold query about 10.5s", "no vector ANN", "no cross-encoder"],
    "files": ["backend/pipeline/retrieval_v3.py", "backend/pipeline/generation_v3.py", "backend/pipeline/ingestion_v3.py"],
  },
  "v3.1": {
    "label": "V3.1 Clean Baseline",
    "purpose": "Final extraction-recall baseline for the current research cycle.",
    "retrieval": ["BM25 hierarchical retrieval", "document-balanced synthesis", "document-balanced extraction", "up to 16 extraction chunks"],
    "ranking": ["MMR plus term diversity", "concrete mechanism prioritization", "preserved rerank evidence terms"],
    "context": ["document-balanced packing", "parent expansion", "evidence-first extraction context"],
    "answering": ["strict cited extraction/synthesis", "limitations and production-stack templates", "Ollama-only model policy"],
    "strengths": ["warmed synthesis 164-194ms", "algorithm extraction 579ms", "best local mechanism recall"],
    "limits": ["cold query about 10s", "no dense vector retrieval", "no RRF", "no cross-encoder"],
    "files": ["backend/pipeline/retrieval_v31.py", "backend/pipeline/generation_v31.py", "backend/pipeline/ingestion_v31.py"],
  },
}
