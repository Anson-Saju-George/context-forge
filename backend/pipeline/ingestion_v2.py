import re
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException


SUPPORTED_SUFFIXES = {".md", ".mdx", ".txt", ".pdf", ".docx"}


def sanitize_filename(filename: str) -> str:
  name = Path(filename).name
  stem = Path(name).stem.lower()
  suffix = Path(name).suffix.lower()
  safe_stem = re.sub(r"[^a-z0-9_-]+", "_", stem).strip("_") or "document"
  return f"{safe_stem}{suffix}"


def extract_text_segments(raw_bytes: bytes, suffix: str, original_filename: str) -> list[dict]:
  if suffix in {".md", ".mdx", ".txt"}:
    try:
      return [{"page": None, "text": raw_bytes.decode("utf-8")}]
    except UnicodeDecodeError as error:
      raise HTTPException(
        status_code=400,
        detail=f"Could not decode {original_filename} as UTF-8 text.",
      ) from error

  if suffix == ".pdf":
    try:
      from pypdf import PdfReader

      reader = PdfReader(BytesIO(raw_bytes))
      return [
        {"page": page_number, "text": page.extract_text() or ""}
        for page_number, page in enumerate(reader.pages, start=1)
      ]
    except ImportError as error:
      raise HTTPException(
        status_code=500,
        detail="PDF ingestion requires pypdf. Install it with: pip install pypdf",
      ) from error
    except Exception as error:
      raise HTTPException(
        status_code=400,
        detail=f"Could not extract text from PDF: {original_filename}",
      ) from error

  if suffix == ".docx":
    try:
      from docx import Document

      document = Document(BytesIO(raw_bytes))
      paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
      return [{"page": None, "text": "\n\n".join(paragraphs)}]
    except ImportError as error:
      raise HTTPException(
        status_code=500,
        detail="DOCX ingestion requires python-docx. Install it with: pip install python-docx",
      ) from error
    except Exception as error:
      raise HTTPException(
        status_code=400,
        detail=f"Could not extract text from DOCX: {original_filename}",
      ) from error

  raise HTTPException(status_code=400, detail=f"Unsupported file type: {original_filename}")


def looks_like_heading(block: str) -> bool:
  line = block.strip().splitlines()[0].strip()
  if not line:
    return False

  if line.startswith("#"):
    return True

  if len(line) > 120 or len(line.split()) > 14:
    return False

  if line.endswith((".", ",", ";", ":")):
    return False

  numbered_heading = re.match(r"^(\d+(\.\d+)*|[A-Z])[\).]?\s+[A-Z][A-Za-z0-9 -]+$", line)
  title_case_words = [word for word in re.findall(r"[A-Za-z]+", line) if word[:1].isupper()]
  return bool(numbered_heading) or len(title_case_words) >= max(2, len(line.split()) // 2)


def slugify(value: str) -> str:
  slug = re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_")
  return slug[:80] or "section"


def split_blocks(text: str) -> list[str]:
  cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
  if not cleaned:
    return []

  blocks = []
  for block in re.split(r"\n\s*\n", cleaned):
    stripped = block.strip()
    if stripped:
      blocks.append(stripped)
  return blocks


def build_chunk_records(
  document_id: str,
  original_filename: str,
  stored_filename: str,
  segments: list[dict],
  chunk_size: int = 900,
  overlap: int = 120,
) -> list[dict]:
  records = []
  current_section = Path(original_filename).stem
  buffer = ""
  buffer_page = None
  buffer_section = current_section

  def flush_buffer() -> None:
    nonlocal buffer, buffer_page, buffer_section
    text = buffer.strip()
    if not text:
      return

    chunk_index = len(records)
    section = buffer_section or current_section
    parent_id = f"{document_id}_parent_{slugify(section)}"
    records.append(
      {
        "id": f"{document_id}_chunk_{chunk_index:04d}",
        "document_id": document_id,
        "text": text,
        "chunk_index": chunk_index,
        "source": stored_filename,
        "original_filename": original_filename,
        "page": buffer_page,
        "section": section,
        "parent_id": parent_id,
      }
    )

    buffer = text[-overlap:] if overlap and len(text) > overlap else ""
    buffer_page = None
    buffer_section = section

  for segment in segments:
    page = segment.get("page")
    page_label = f"Page {page}" if page else current_section

    for block in split_blocks(segment.get("text", "")):
      if looks_like_heading(block):
        current_section = block.strip().splitlines()[0].strip("# ").strip()

      section = current_section or page_label
      next_piece = block.strip()
      projected_size = len(buffer) + len(next_piece) + 2

      if buffer and projected_size > chunk_size:
        flush_buffer()

      if not buffer:
        buffer_page = page
        buffer_section = section

      buffer = f"{buffer}\n\n{next_piece}".strip()

      while len(buffer) > chunk_size * 1.35:
        split_at = buffer.rfind(" ", 0, chunk_size)
        if split_at < chunk_size * 0.5:
          split_at = chunk_size

        chunk_text = buffer[:split_at].strip()
        remaining = buffer[max(0, split_at - overlap):].strip()
        buffer = chunk_text
        flush_buffer()
        buffer = remaining
        buffer_page = page
        buffer_section = section

  flush_buffer()
  return records
