import os
import json
import logging
from typing import List, Dict, Any, Tuple
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)

# Pydantic schemas for Gemini Structured Output
class SummarySchema(BaseModel):
    summary: str = Field(description="A concise executive summary paragraph, 3-5 sentences long.")
    key_findings: List[str] = Field(description="Top 5 key findings and highlights from the document content.")
    important_dates: List[str] = Field(description="List of important dates and events formatted as 'YYYY-MM-DD: Event Description'.")

class GeminiService:
    _instance = None
    _configured = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GeminiService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization logspam
        if not self._configured:
            self.model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
            self.client = None
            self.use_mock = True
            self._configure_client()
            self._configured = True

    def _configure_client(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if self.api_key:
            logger.info(f"Configuring Gemini Client with model '{self.model_name}'...")
            self.client = genai.Client(api_key=self.api_key)
            self.use_mock = False
        else:
            logger.warning("GEMINI_API_KEY environment variable is not set. Falling back to local heuristic/mock RAG generation.")
            self.use_mock = True

    def is_available(self) -> bool:
        """
        Dynamically checks if the API key is configured.
        Loads environment changes on the fly.
        Returns whether answer generation is available. The local heuristic
        fallback remains usable when a Gemini key is not configured.
        """
        from dotenv import load_dotenv
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if self.api_key:
            if self.client is None:
                self.client = genai.Client(api_key=self.api_key)
            self.use_mock = False
        else:
            self.use_mock = True
        return True

    def is_remote_available(self) -> bool:
        """Return whether the Gemini API is configured (without making a network call)."""
        self.is_available()
        return not self.use_mock

    def generate_answer(
        self, 
        query: str, 
        context_chunks: List[Dict[str, Any]], 
        chat_history: List[Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generates an answer to the user query using the retrieved context chunks and chat history.
        """
        self.is_available()
        if self.use_mock:
            return self._generate_mock_answer(query, context_chunks, chat_history)

        # 1. Format the context
        context_str = ""
        citations = []
        for idx, chunk in enumerate(context_chunks):
            meta = chunk["metadata"]
            citation = {
                "document_id": meta["document_id"],
                "filename": meta["filename"],
                "page": meta["page_number"],
                "text": chunk["text"]
            }
            citations.append(citation)
            
            context_str += f"[{idx+1}] File: {meta['filename']} | Page: {meta['page_number']}\nContent: {chunk['text']}\n\n"

        # 2. Build the system instruction prompt
        system_prompt = (
            "You are an expert AI document assistant. Your task is to answer user questions based ONLY on the "
            "provided document context blocks. If the context does not contain the answer, explicitly state "
            "that you cannot find the answer in the provided documents. DO NOT make up answers, assume facts, "
            "or use general knowledge outside the context.\n\n"
            "Format your answer cleanly with markdown. When referring to facts in the context, cite them by "
            "appending [idx] (e.g., [1], [2]) corresponding to the context blocks.\n\n"
            f"Here is the context to use:\n{context_str}"
        )

        try:
            logger.info(f"Sending request to Gemini API ({self.model_name})...")
            # 3. Create GenerativeModel with system instructions
            # 3. Format history for Gemini chat structure.
            gemini_history = []
            for msg in chat_history[-10:]:
                role = "user" if msg["role"] == "user" else "model"
                gemini_history.append({
                    "role": role,
                    "parts": [msg["content"]]
                })

            # 4. Start chat session
            chat = self.client.chats.create(
                model=self.model_name,
                history=gemini_history,
                config=types.GenerateContentConfig(system_instruction=system_prompt)
            )
            response = chat.send_message(query)
            return response.text, citations
            
        except Exception as e:
            logger.error(f"Failed to generate answer from Gemini API: {e}")
            logger.info("Falling back to local context-based answer generation.")
            return self._generate_mock_answer(query, context_chunks, chat_history)

    def generate_summary(self, document_text: str) -> Dict[str, Any]:
        """
        Generates an executive summary, key findings, and important dates from document text
        using Gemini's native Structured Output format.
        """
        self.is_available()
        if self.use_mock:
            return self._generate_mock_summary(document_text)

        default_res = {
            "summary": "Summary generation was not possible or timed out.",
            "key_findings": [],
            "important_dates": []
        }

        # Truncate text if it's too long (limit to approx 80,000 characters to prevent token limits)
        truncated_text = document_text
        if len(document_text) > 80000:
            truncated_text = document_text[:50000] + "\n\n[... TEXT TRUNCATED FOR SUMMARIZATION ...]\n\n" + document_text[-30000:]

        prompt = (
            "Analyze the following document text and extract:\n"
            "1. A concise Executive Summary (1 paragraph, 3-5 sentences).\n"
            "2. Top 5 Key Findings (bulleted list).\n"
            "3. Important Dates mentioned in the document and events associated with them.\n\n"
            f"Document Text:\n{truncated_text}"
        )

        try:
            logger.info("Sending request to Gemini API for structured summarization...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SummarySchema
                )
            )

            parsed = response.parsed
            result = parsed.model_dump() if isinstance(parsed, BaseModel) else json.loads(response.text)
            return {
                "summary": result.get("summary", ""),
                "key_findings": result.get("key_findings", []),
                "important_dates": result.get("important_dates", [])
            }
            
        except Exception as e:
            logger.error(f"Failed to generate structured summary from Gemini API: {e}")
            logger.info("Falling back to local heuristic summary generation.")
            return self._generate_mock_summary(document_text)

    def _generate_mock_summary(self, text: str) -> Dict[str, Any]:
        """
        Generates a realistic summary from the document text using heuristics.
        """
        import re
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        
        # 1. Executive Summary: take the first 3-5 sentences that look like intro
        intro_sentences = []
        for s in sentences[:15]:
            if len(s) > 40 and not any(k in s.lower() for k in ["table", "contents", "index", "page"]):
                intro_sentences.append(s)
                if len(intro_sentences) >= 4:
                    break
        summary = " ".join(intro_sentences) if intro_sentences else "This document contains analyzed text sections. The source content has been indexed and is ready for semantic querying."
        
        # 2. Key Findings: look for sentences containing conclusions or results
        findings = []
        finding_keywords = ["finding", "result", "important", "conclude", "showed", "significant", "recommend", "key", "established", "demonstrated"]
        for s in sentences:
            if any(k in s.lower() for k in finding_keywords) and len(s) > 50 and len(s) < 150:
                clean_s = re.sub(r'\s+', ' ', s)
                if clean_s not in findings:
                    findings.append(clean_s)
                if len(findings) >= 5:
                    break
                    
        # Fallback if not enough findings
        if len(findings) < 5:
            for s in sentences:
                if len(s) > 60 and len(s) < 120 and s not in findings:
                    findings.append(re.sub(r'\s+', ' ', s))
                    if len(findings) >= 5:
                        break
        if not findings:
            findings = ["Document structure indexed successfully.", "Main text segments partitioned and stored.", "Keywords and terminology parsed.", "Metadata links set to active.", "Content ready for conversational retrieval."]
            
        # 3. Important Dates: look for date formats (e.g. YYYY-MM-DD, Month DD, YYYY)
        dates = []
        date_pattern = r'\b(?:(?:19|20)\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}|\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4})\b'
        
        seen_dates = set()
        for s in sentences:
            found_dates = re.findall(date_pattern, s)
            for d in found_dates:
                if d not in seen_dates:
                    seen_dates.add(d)
                    clean_context = re.sub(r'\s+', ' ', s)
                    if len(clean_context) > 120:
                        clean_context = clean_context[:117] + "..."
                    dates.append(f"{d}: {clean_context}")
                if len(dates) >= 5:
                    break
            if len(dates) >= 5:
                break
                
        if not dates:
            dates = ["No specific dates detected in the text structure."]
            
        return {
            "summary": summary,
            "key_findings": findings[:5],
            "important_dates": dates[:5]
        }

    def _generate_mock_answer(
        self, 
        query: str, 
        context_chunks: List[Dict[str, Any]], 
        chat_history: List[Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Generate a useful extractive answer when the remote model is unavailable."""
        if not context_chunks:
            return "I could not find any relevant information in the uploaded documents to answer your question.", []

        import re
        stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for",
            "from", "how", "i", "in", "is", "it", "me", "of", "on", "or", "please",
            "that", "the", "this", "to", "what", "when", "where", "which", "with", "you"
        }
        follow_up_words = {"elaborate", "explain", "expand", "more", "detail", "continue", "why", "how"}

        previous_query = ""
        for message in reversed(chat_history):
            if message.get("role") == "user" and message.get("content", "").strip():
                previous_query = message["content"].strip()
                break

        query_tokens = set(re.findall(r"[a-z0-9]+", query.lower())) - stop_words
        is_follow_up = bool(query_tokens & follow_up_words) or len(query_tokens) <= 2
        search_query = f"{previous_query} {query}" if is_follow_up and previous_query else query
        search_tokens = set(re.findall(r"[a-z0-9]+", search_query.lower())) - stop_words - follow_up_words

        candidates = []
        for chunk_index, chunk in enumerate(context_chunks):
            text = re.sub(r"\s+", " ", chunk.get("text", "")).strip()
            if not text:
                continue
            sentences = re.split(r"(?<=[.!?])\s+|\s*[•▪]\s*|\n+", text)
            for sentence_index, sentence in enumerate(sentences):
                sentence = sentence.strip(" -\t")
                if len(sentence) < 25:
                    continue
                words = set(re.findall(r"[a-z0-9]+", sentence.lower()))
                overlap = len(words & search_tokens)
                # Retrieval order is already semantic, while overlap improves exact matches.
                score = overlap * 10 - chunk_index - (sentence_index * 0.05)
                if 40 <= len(sentence) <= 500:
                    score += 1
                candidates.append((score, overlap, chunk_index, sentence))

        if not candidates:
            candidates = [(0, 0, 0, re.sub(r"\s+", " ", context_chunks[0]["text"]).strip()[:1200])]

        candidates.sort(key=lambda item: item[0], reverse=True)
        if any(item[1] > 0 for item in candidates):
            candidates = [item for item in candidates if item[1] > 0]
        max_points = 8 if is_follow_up else 5
        selected = []
        seen = set()
        for _, _, chunk_index, sentence in candidates:
            normalized = re.sub(r"\W+", " ", sentence.lower()).strip()
            if normalized in seen:
                continue
            seen.add(normalized)
            selected.append((chunk_index, sentence))
            if len(selected) >= max_points:
                break

        used_chunk_indexes = []
        for chunk_index, _ in selected:
            if chunk_index not in used_chunk_indexes:
                used_chunk_indexes.append(chunk_index)

        citations = []
        citation_number = {}
        for chunk_index in used_chunk_indexes:
            chunk = context_chunks[chunk_index]
            meta = chunk["metadata"]
            citation_number[chunk_index] = len(citations) + 1
            citations.append({
                "document_id": meta["document_id"],
                "filename": meta["filename"],
                "page": meta["page_number"],
                "text": chunk["text"]
            })

        subject = previous_query if is_follow_up and previous_query else query
        points = "\n".join(
            f"- {sentence} [{citation_number[chunk_index]}]"
            for chunk_index, sentence in selected
        )
        answer = f"Here is a document-grounded explanation of **{subject.strip()}**:\n\n{points}"
        if is_follow_up:
            answer += "\n\nThese points expand on the relevant sections found in the document."
        return answer, citations

# Instantiate singleton helper
gemini_service = None

def get_llm_service() -> GeminiService:
    global gemini_service
    if gemini_service is None:
        gemini_service = GeminiService()
    return gemini_service
