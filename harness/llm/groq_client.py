"""Groq model client for autonomous reasoning, failure diagnosis explanation, and code patch synthesis."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("harness.llm.groq")

SUPPORTED_GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]


class GroqClient:
    """Client for querying Groq LLM API with built-in retries, fallbacks, and deterministic heuristics."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.api_key: str = (api_key or os.getenv("GROQ_API_KEY", "")).strip()
        self.model: str = (model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")).strip()
        self.base_url: str = (
            base_url or os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        ).rstrip("/")
        self.timeout_seconds: float = timeout_seconds

    @property
    def is_configured(self) -> bool:
        """Return True if an authentic Groq API key is configured."""
        return bool(
            self.api_key
            and not self.api_key.startswith("your_")
            and not self.api_key.startswith("change_me")
        )

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> Dict[str, Any]:
        """Execute a chat completion request against Groq's OpenAI-compatible endpoint.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Optional model override.
            temperature: Sampling temperature.
            max_tokens: Max output tokens.

        Returns:
            Dict containing 'content', 'model', 'usage', and 'source'.
        """
        if not self.is_configured:
            logger.debug("Groq API key not configured; returning empty response.")
            return {
                "content": "",
                "model": self.model,
                "usage": {},
                "source": "unconfigured_fallback",
            }

        target_model = model or self.model
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "TrueForge-Agent-Harness/0.2.0",
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                res_bytes = response.read()
                data = json.loads(res_bytes.decode("utf-8"))
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                return {
                    "content": content,
                    "model": data.get("model", target_model),
                    "usage": data.get("usage", {}),
                    "source": "groq_api",
                }
        except urllib.error.HTTPError as http_err:
            error_body = ""
            try:
                error_body = http_err.read().decode("utf-8")
            except Exception:
                pass
            logger.error("Groq API HTTPError %s: %s", http_err.code, error_body)
            return {
                "content": f"[Groq API Error {http_err.code}: {http_err.reason}]",
                "error": error_body,
                "model": target_model,
                "source": "groq_api_error",
            }
        except Exception as err:
            logger.error("Groq API connection error: %s", err)
            return {
                "content": f"[Groq Connection Error: {str(err)}]",
                "error": str(err),
                "model": target_model,
                "source": "groq_connection_error",
            }

    def explain_diagnostic_report(self, report: Dict[str, Any]) -> str:
        """Generate a natural-language reliability engineering explanation from a Causal DAG report."""
        summary = report.get("summary", "Unknown failure")
        causal_chain = report.get("causal_chain", [])
        primary_fault = report.get("primary_fault_category", "HARDWARE_TRANSIENT")

        chain_text = "\n".join(
            f"- [{node.get('category', 'EVENT')}] {node.get('summary', '')} at t={node.get('timestamp', 0):.2f}s"
            for node in causal_chain
        )

        if not self.is_configured:
            return (
                f"### Root Cause Diagnosis Summary (Deterministic Heuristic)\n"
                f"- **Primary Fault Category:** `{primary_fault}`\n"
                f"- **Summary:** {summary}\n\n"
                f"#### Causal Propagation Sequence:\n"
                f"{chain_text if chain_text else '- No causal events recorded.'}\n\n"
                f"> *Tip: Configure `GROQ_API_KEY` in `.env` to enable AI deep reasoning and synthesis via {self.model}.*"
            )

        system_prompt = (
            "You are TrueForge AI Reliability Architect, an expert in cyber-physical systems, "
            "deterministic robotics simulation, and autonomous vehicle safety. "
            "Analyze the causal DAG telemetry failure report and provide a crisp, authoritative diagnosis."
        )

        user_prompt = (
            f"Here is the autonomous vehicle failure diagnostic report:\n\n"
            f"Primary Category: {primary_fault}\n"
            f"Summary: {summary}\n"
            f"Causal Chain Nodes:\n{chain_text}\n\n"
            f"Provide:\n"
            f"1. A concise explanation of the root cause mechanism.\n"
            f"2. How hardware perturbations (latency, compute deadlines, or mechanical lag) cascaded into the safety violation.\n"
            f"3. Specific recommended control-theoretic or software guardrail remediations."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        resp = self.chat_completion(messages, temperature=0.2)
        if resp.get("source") == "groq_api" and resp.get("content"):
            return resp["content"]

        return f"### Root Cause Diagnosis\n{summary}\n\nCausal Chain:\n{chain_text}"

    def synthesize_patch_guidance(
        self,
        original_code: str,
        diagnostic_report: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate AI-assisted patch recommendations and code hardening snippets."""
        if not self.is_configured:
            return {
                "source": "deterministic_patcher",
                "recommended_strategies": [
                    "DYNAMIC_STOPPING_BUFFER",
                    "STALE_SENSOR_FAIL_SAFE",
                ],
                "explanation": (
                    "Using TrueForge AST deterministic auto-patcher. "
                    "Configure GROQ_API_KEY in .env for Groq LLM-assisted code generation."
                ),
            }

        diag_summary = (
            diagnostic_report.get("summary", "") if diagnostic_report else "General reliability hardening"
        )
        fault_cat = (
            diagnostic_report.get("primary_fault_category", "LATENCY_OR_COMPUTE")
            if diagnostic_report
            else "SYSTEM"
        )

        system_prompt = (
            "You are TrueForge AST Hardening Architect. Analyze the Python controller code and failure context, "
            "and suggest AST hardening strategies to survive sensor delays, thermal throttling, and actuator lag."
        )

        user_prompt = (
            f"Failure Diagnosis: {diag_summary} (Category: {fault_cat})\n\n"
            f"Target Controller Code:\n```python\n{original_code}\n```\n\n"
            f"Recommend the best hardening approach to guarantee safety under hardware latency and compute degradation."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        resp = self.chat_completion(messages, temperature=0.1, max_tokens=1000)
        return {
            "source": resp.get("source", "groq_api"),
            "model": resp.get("model", self.model),
            "guidance": resp.get("content", ""),
            "recommended_strategies": [
                "DYNAMIC_STOPPING_BUFFER",
                "STALE_SENSOR_FAIL_SAFE",
            ],
        }


# Global singleton instance
default_groq_client = GroqClient()


def get_groq_client() -> GroqClient:
    """Retrieve freshly configured default GroqClient."""
    return GroqClient()
