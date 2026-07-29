from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
  role: Literal["system", "user", "assistant"]
  content: str


class ChatRequest(BaseModel):
  message: str
  provider: Literal["auto", "ollama"] = "auto"
  model: str | None = None
  messages: list[ChatMessage] = Field(default_factory=list)
  chat_id: str = "default"
  use_retrieval: bool = True
  rag_version: str = "v3.1"


class RetrievalResult(BaseModel):
  chunk_id: str
  document_id: str
  source: str
  original_filename: str
  text: str
  score: float
  page: int | None = None
  section: str = ""
  parent_id: str = ""
  rerank_score: float | None = None
  rerank_reasons: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
  answer: str
  provider: str
  model: str
  latency_ms: int
  fallback_used: bool = False
  reasoning_summary: str = ""
  citations: list[RetrievalResult] = Field(default_factory=list)
  retrieval: dict = Field(default_factory=dict)


class IngestedDocument(BaseModel):
  id: str
  original_filename: str
  stored_filename: str
  upload_order: int
  chunk_count: int


class IngestResponse(BaseModel):
  chat_id: str
  documents: list[IngestedDocument] = Field(default_factory=list)
  total_documents: int
  total_chunks: int


class RetrieveRequest(BaseModel):
  query: str
  chat_id: str = "default"
  top_k: int | None = None
  rag_version: str = "v3.1"


class ClearDocumentsRequest(BaseModel):
  chat_id: str = "default"


class CreateChatRequest(BaseModel):
  title: str = ""


class RenameChatRequest(BaseModel):
  title: str = ""


class GoogleAuthRequest(BaseModel):
  credential: str


class AuthUser(BaseModel):
  sub: str
  email: str = ""
  name: str = ""
  picture: str = ""
  is_admin: bool = False
  paid: bool = False
  exp: int = 0


class AuthResponse(BaseModel):
  token: str
  user: AuthUser


class PaymentOrderResponse(BaseModel):
  key_id: str
  order_id: str
  amount: int
  currency: str
  name: str = "ContextForge"
  description: str = "One hour ContextForge access"


class PaymentVerifyRequest(BaseModel):
  razorpay_order_id: str
  razorpay_payment_id: str
  razorpay_signature: str


class RetrieveResponse(BaseModel):
  query: str
  mode: str
  results: list[RetrievalResult] = Field(default_factory=list)
  total_chunks: int
  latency_ms: int
