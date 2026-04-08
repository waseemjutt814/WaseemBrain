from __future__ import annotations

import re
import zipfile
from io import BytesIO

from ..types import NormalizedSignal, Result, err, ok
from .base import InputAdapter

_MAX_TEXT_LENGTH = 4000


class DocumentAdapter(InputAdapter):
    def __init__(self, filename_hint: str | None = None) -> None:
        self._filename_hint = filename_hint or "document.bin"

    def normalize(self, raw_input: object) -> Result[NormalizedSignal, str]:
        if not isinstance(raw_input, bytes):
            return err("DocumentAdapter expects file bytes")

        filename = self._filename_hint.lower()
        if filename.endswith(".pdf"):
            extracted = self._extract_pdf_text(raw_input)
        elif filename.endswith(".docx"):
            extracted = self._extract_docx_text(raw_input)
        else:
            extracted = self._extract_plaintext(raw_input)

        text = extracted.strip()
        if not text:
            return err(f"No extractable text found in {self._filename_hint}")
        if len(text) > _MAX_TEXT_LENGTH:
            text = f"{text[:_MAX_TEXT_LENGTH].rstrip()}\n[truncated]"

        return ok(
            {
                "text": text,
                "modality": "file",
                "metadata": {
                    "filename": self._filename_hint,
                    "length": len(text),
                },
            }
        )

    def _extract_pdf_text(self, raw_bytes: bytes) -> str:
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception:
            return self._extract_printable_strings(raw_bytes)

        try:
            reader = PdfReader(BytesIO(raw_bytes))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                return text
        except Exception:
            # Fallback to printable strings if PDF parsing fails
            pass
        
        return self._extract_printable_strings(raw_bytes)

    def _extract_docx_text(self, raw_bytes: bytes) -> str:
        try:
            from docx import Document  # type: ignore
        except Exception:
            return self._extract_docx_xml(raw_bytes)

        document = Document(BytesIO(raw_bytes))
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)

    def _extract_docx_xml(self, raw_bytes: bytes) -> str:
        with zipfile.ZipFile(BytesIO(raw_bytes)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        return re.sub(r"<[^>]+>", " ", xml)

    def _extract_plaintext(self, raw_bytes: bytes) -> str:
        return raw_bytes.decode("utf-8", errors="ignore")

    def _extract_printable_strings(self, raw_bytes: bytes) -> str:
        matches = re.findall(rb"[ -~]{4,}", raw_bytes)
        return "\n".join(chunk.decode("utf-8", errors="ignore") for chunk in matches)
