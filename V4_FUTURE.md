# ContextForge V4 Future Direction

V4 is not implemented in the current codebase. It is the proposed next architecture after the V3.1 research cycle.

## Working Name

V4 Hybrid Evidence Planner

## Goal

Combine the reliability of V3.1 retrieval accountability with the readability of local model generation.

The current benchmark showed a clear split:

- Deterministic mode gives stronger evidence discipline and repeatable benchmark answers.
- Ollama mode exercises real model inference and GPU/VRAM behavior, but small local models can still produce generic or weakly grounded answers.

V4 should bridge those two modes.

## Proposed Pipeline

```text
query
retrieve with V3.1 evidence-first retrieval
build deterministic evidence plan
compress and organize source-grounded facts
send the evidence plan to Ollama
generate polished answer
validate citations and mechanism coverage
return answer plus telemetry
```

## Core Ideas

- Evidence plan before generation.
- Source-balanced context from V3.1.
- Deterministic extraction of document roles, mechanisms, and tradeoffs.
- Ollama used for final prose, not for discovering unsupported facts.
- Citation and mechanism coverage checks after generation.
- Clear telemetry split between retrieval latency, planning latency, generation latency, and validation latency.

## Expected Strengths

- More natural answers than deterministic templates.
- Better grounding than direct Ollama generation.
- GPU-visible inference for demos and deployment tests.
- Less hallucination freedom than pure model generation.
- Better explanation quality for long cross-document synthesis prompts.

## Known Risks

- Higher latency than deterministic mode.
- More moving parts than V3.1.
- Requires strict prompts and post-generation validation.
- Small local models may still over-compress or generalize unless the evidence plan is explicit.

## Success Criteria

- Keeps V3.1 source coverage and mechanism recall.
- Produces more readable answers than deterministic synthesis.
- Does not introduce unsupported concepts from the model.
- Shows separate retrieval, planning, generation, and total latency.
- Works with the approved local models: `gemma4:e2b` and `qwen3:4b-instruct`.
