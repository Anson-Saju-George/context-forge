# ContextForge Benchmark Output

## Final Research Interpretation

The benchmark run is valuable because it shows the evolution of retrieval architecture maturity across versions.

The main result is not that every later version is universally more fluent. The main result is that later versions are more controlled, more accountable, and more reliable as retrieval systems.

## Version Character

| Version | Identity | Biggest characteristic |
| --- | --- | --- |
| V0 | Similarity toy | Semantic drift |
| V1 | Sparse retrieval baseline | Surprisingly fluent |
| V2 | Routed retrieval | Architectural organization emerges |
| V3 | Benchmark retrieval | Disciplined evidence |
| V3.1 | Evidence-first IR | Retrieval accountability |

## Key Findings

V0 is useful as a comparison point, but it shows the expected toy-RAG failure modes:

- retrieval contamination
- weak document balance
- shallow evidence
- no retrieval discipline
- higher hallucination risk

V1 is stronger than expected in conversational quality. The local model compensates heavily, so the answer can feel smart even when the evidence is less precise. This is the classic right-topic, wrong-evidence failure mode.

V2 is the turning point where the system becomes orchestrated retrieval rather than only an LLM answering over chunks. Intent routing, document-balanced synthesis, and mechanism-aware retrieval start to appear clearly.

V3 is more disciplined. It trades some fluency for evidence density, source coverage, benchmark repeatability, and stronger retrieval control.

V3.1 behaves most like retrieval middleware. It is less chatbot-like and more retrieval-accountable: cleaner terminology, stronger evidence discipline, fewer unsupported mechanism jumps, and better benchmark reliability.

## Important Distinction

The project did not simply make answers sound smarter.

It progressively:

- reduced hallucination freedom
- increased retrieval control
- increased evidence accountability
- increased deterministic behavior
- improved source coverage and mechanism recall

That is why later versions can feel less magical while being more trustworthy.

## Benchmark Reality

| Optimization target | Best fit |
| --- | --- |
| Conversational fluency | V1 with Ollama generation |
| Failure-mode demonstration | V0 |
| First mature retrieval architecture | V2 |
| Benchmark reliability | V3 |
| Evidence accountability | V3.1 |

## Final Assessment

| Version | Quality |
| --- | --- |
| V0 | Weak but educational |
| V1 | Deceptively strong |
| V2 | First architecturally mature version |
| V3 | First benchmark-grade version |
| V3.1 | First retrieval-accountable version |

## Closing Note

By V3.1, ContextForge is no longer only a RAG chatbot experiment. It is a retrieval orchestration framework with versioned retrieval behavior, evidence telemetry, citations, and benchmarkable output paths.

The proposed V4 direction is documented in `V4_FUTURE.md`: deterministic evidence planning plus Ollama prose generation.

## Qwen 3 4B Ollama Run

The same sixth production-stack question was tested with `qwen3:4b-instruct` in forced Ollama mode.

Logs:

- `backend/reports/ultimate_runs/ultimate_run_2026-05-12_17-04-43.txt`: V0 and V1 completed; V2 timed out before the timeout setting was increased.
- `backend/reports/ultimate_runs/ultimate_run_2026-05-12_17-08-33.txt`: V2, V3, and V3.1 completed after setting `OLLAMA_TIMEOUT_SECONDS=120`.

Latency summary:

| Version | Provider | Model | Retrieval mode | Total latency | Retrieval latency |
| --- | --- | --- | --- | ---: | ---: |
| V0 | Ollama | qwen3:4b-instruct | v0_token_similarity | 14446ms | 382ms |
| V1 | Ollama | qwen3:4b-instruct | bm25_hierarchical | 8245ms | 985ms |
| V2 | Ollama | qwen3:4b-instruct | bm25_hierarchical_synthesis | 49518ms | 7720ms |
| V3 | Ollama | qwen3:4b-instruct | bm25_hierarchical_synthesis | 53655ms | 10236ms |
| V3.1 | Ollama | qwen3:4b-instruct | bm25_hierarchical_synthesis | 52655ms | 10644ms |

Main observations:

- The forced-Ollama path works and exercises real local model inference.
- Qwen needed a longer backend timeout than Gemma for the longer synthesis prompt.
- V0 again showed the retrieval gap clearly: it retrieved mostly weak/imbalanced evidence and the model explicitly noted missing RAG context.
- V1 retrieved broader sources but produced unstable public-output behavior in this run.
- V2/V3/V3.1 gave the model much better source coverage, but Qwen still added formatting noise and some overconfident claims.
- V3.1 remained the strongest retrieval substrate, even when the generation model was less controlled than deterministic synthesis.

Conclusion:

Qwen is useful for stress-testing forced local inference and GPU behavior, but the benchmark confirms the same architecture lesson: retrieval accountability and generation fluency are separate concerns. This supports the future V4 direction: deterministic evidence planning first, then Ollama generation over that plan.

## Model Sensitivity Finding

The Qwen run changes the interpretation of the benchmark.

The differences are no longer only retrieval differences. They now show model personality interacting with retrieval architecture.

Earlier versions were dominated by retrieval failure. Once the retrieval stack matured, especially in V2, V3, and V3.1, model capability became visible:

- reasoning quality
- synthesis structure
- architectural layering
- explanatory richness
- willingness to infer beyond retrieved evidence

This is a major systems milestone: ContextForge is now strong enough to compare retrieval-conditioned model behavior, not only raw retrieval quality.

## Gemma vs Qwen

| Model | Behavior |
| --- | --- |
| Gemma | Safer grounding, compressed answers, more conservative synthesis, stronger retrieval discipline |
| Qwen | Richer synthesis, stronger architectural chaining, higher technical density, more inferential expansion |

Gemma mostly produced broad summaries and grouped concepts. Qwen repeatedly built causal architectural chains:

```text
Transformer -> Llama 2 -> RAG -> Kubernetes
```

Qwen also preserved more technical density, including mechanisms such as grouped-query attention, MIPS, FAISS compression, optimizer details, and Kubernetes operational components.

## Qwen Tradeoff

Qwen is stronger, but also more dangerous.

It is more willing to complete missing architecture patterns and add plausible system details. That creates better synthesis when the retrieval context is good, but it can also introduce unsupported material when retrieval is weak or incomplete.

This creates the core model tradeoff:

| Gemma | Qwen |
| --- | --- |
| Safer grounding | Richer synthesis |
| Conservative | Inferential |
| Compressed | Expansive |
| Retrieval-disciplined | Architecture-driven |
| Lower hallucination tendency | Higher extrapolation tendency |

## Version Behavior With Qwen

| System | Behavior |
| --- | --- |
| V0 + Qwen | Dangerous hallucination machine |
| V1 + Qwen | Smart but unstable |
| V2 + Qwen | Architecturally coherent |
| V3 + Qwen | Strong systems reasoning |
| V3.1 + Qwen | Disciplined systems synthesis |

This makes the V3/V3.1 difference clearer:

- V3 is more expansive and gives the model more inferential freedom.
- V3.1 is cleaner, more disciplined, and better layered around retrieved evidence.

## Key Insight

Qwen only became this useful after retrieval matured.

Strong instruct models amplify both good retrieval and bad retrieval. On weak retrieval, they can hallucinate confidently. On mature retrieval, they can exploit dense evidence and produce high-quality systems reasoning.

That means ContextForge has crossed an important threshold:

```text
retrieval quality is no longer the only bottleneck
model behavior is now measurable through the retrieval system
```

The project has moved from toy RAG comparison into real retrieval systems engineering.
