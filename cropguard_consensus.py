"""Cost-conscious parallel diagnostic consensus for CropGuard AI.

Gemini vision, local ONNX inference, and optional Google Custom Search run in
parallel. A configured local Ollama model then checks the resulting hypothesis;
without Ollama, a deterministic knowledge-base compatibility check is used.
Scores are heuristic screening signals, not calibrated probabilities.
"""

from __future__ import annotations

import json
import re
import base64
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

import requests

import disease_data


LocalVision = Callable[[], Mapping[str, Any]]
ProgressCallback = Callable[[str, str], None]

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_SEARCH_RESULTS = 5


@dataclass(frozen=True)
class VisionResult:
    detected_crop: str
    health_status: str
    primary_diagnosis: str
    visual_symptoms: list[str]
    confidence_score: float
    provider: str
    error: str | None = None


@dataclass(frozen=True)
class LocalResult:
    available: bool
    detected_crop: str = ""
    primary_diagnosis: str = ""
    confidence_score: float = 0.0
    confidence_margin: float = 0.0
    health_status: str = "unknown"
    provider: str = "local ONNX"
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReasoningResult:
    supported: bool | None
    explanation: str
    alternatives: list[str] = field(default_factory=list)
    provider: str = "knowledge-base cross-check"
    error: str | None = None


@dataclass(frozen=True)
class SearchResult:
    available: bool
    results: list[dict[str, str]] = field(default_factory=list)
    message: str = "Live regional search is not configured."
    error: str | None = None


@dataclass(frozen=True)
class ConsensusReport:
    detected_crop: str
    health_status: str
    primary_diagnosis: str
    disease_key: str | None
    visual_symptoms: list[str]
    consensus_confidence_index: float
    confidence_is_calibrated: bool
    agreement: str
    vision: VisionResult
    local_vision: LocalResult
    reasoning: ReasoningResult
    web_grounding: SearchResult
    region: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation for Streamlit session state."""
        return asdict(self)


class AgentError(RuntimeError):
    """An expected failure at an external or local-model agent boundary."""


def _config_value(config: Mapping[str, Any], key: str, default: str = "") -> str:
    value = config.get(key, default)
    return value.strip() if isinstance(value, str) else default


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _crop_family(crop_name: str) -> str | None:
    normalized_crop = f" {_normalize(crop_name)} "
    matches: list[tuple[int, str]] = []
    for family, info in disease_data.CROP_FAMILIES.items():
        for synonym in info[3]:
            normalized_synonym = _normalize(synonym)
            if normalized_synonym and f" {normalized_synonym} " in normalized_crop:
                matches.append((len(normalized_synonym), family))
    if not matches:
        return None
    longest = max(length for length, _ in matches)
    families = {family for length, family in matches if length == longest}
    return next(iter(families)) if len(families) == 1 else None


def _disease_key(crop_name: str, diagnosis: str) -> str | None:
    family = _crop_family(crop_name)
    normalized_diagnosis = _normalize(diagnosis)
    if not family or not normalized_diagnosis:
        return None

    exact: set[str] = set()
    contained: dict[str, int] = {}
    padded_diagnosis = f" {normalized_diagnosis} "
    for key, entry in disease_data.DISEASES.items():
        if entry.get("crops") and family not in entry["crops"]:
            continue
        variants = [entry["epi"], *entry["name"], *entry["alias"]]
        for variant in variants:
            normalized_variant = _normalize(variant)
            if len(normalized_variant) < 4:
                continue
            if normalized_variant == normalized_diagnosis:
                exact.add(key)
            elif f" {normalized_variant} " in padded_diagnosis:
                contained[key] = max(contained.get(key, 0), len(normalized_variant))
            elif padded_diagnosis in f" {normalized_variant} ":
                contained[key] = max(contained.get(key, 0), len(normalized_diagnosis))
    if len(exact) == 1:
        return next(iter(exact))
    if exact or not contained:
        return None
    best_length = max(contained.values())
    best = {key for key, length in contained.items() if length == best_length}
    return next(iter(best)) if len(best) == 1 else None


def _parse_json_object(value: Any, agent_name: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        raise AgentError(f"{agent_name} returned a non-JSON response.")
    cleaned = value.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise AgentError(f"{agent_name} returned invalid JSON.") from error
    if not isinstance(result, dict):
        raise AgentError(f"{agent_name} returned JSON that was not an object.")
    return result


def _validate_vision_payload(payload: Mapping[str, Any]) -> tuple[str, str, str, list[str], float]:
    crop = payload.get("detected_crop")
    status = payload.get("health_status")
    diagnosis = payload.get("primary_diagnosis")
    symptoms = payload.get("visual_symptoms")
    confidence = payload.get("confidence_score")
    if not isinstance(crop, str) or not isinstance(diagnosis, str):
        raise AgentError("Vision response is missing crop or diagnosis text.")
    if not isinstance(status, str):
        status = "unknown"
    status = status.strip().casefold()
    if status not in {"healthy", "diseased", "pest damage", "unknown"}:
        status = "unknown"
    if isinstance(symptoms, str):
        symptoms = [symptoms]
    if not isinstance(symptoms, list) or any(not isinstance(item, str) for item in symptoms):
        symptoms = []
    try:
        confidence_number = float(confidence)
    except (TypeError, ValueError) as error:
        raise AgentError("Vision response has no valid confidence score.") from error
    if not 0.0 <= confidence_number <= 1.0:
        raise AgentError("Vision confidence must be between 0 and 1.")
    return crop.strip(), status, diagnosis.strip(), symptoms[:12], confidence_number


def _request_json(
    method: str,
    url: str,
    *,
    timeout: float,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()
    except requests.Timeout as error:
        raise AgentError("The agent request timed out.") from error
    except requests.RequestException as error:
        raise AgentError(f"The agent request failed: {error}") from error
    try:
        payload = response.json()
    except requests.JSONDecodeError as error:
        raise AgentError("The agent returned an invalid JSON response.") from error
    if not isinstance(payload, dict):
        raise AgentError("The agent response was not a JSON object.")
    return payload


def _gemini_vision(
    image_bytes: bytes,
    mime_type: str,
    selected_crop: str,
    language: str,
    config: Mapping[str, Any],
) -> VisionResult:
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise AgentError("Gemini image request exceeds the 15 MB limit; local ONNX fallback remains available.")
    api_key = _config_value(config, "GEMINI_API_KEY")
    if not api_key:
        raise AgentError("Gemini is not configured; local vision will be used.")
    if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
        raise AgentError("The uploaded image is empty or exceeds the 15 MB limit.")
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise AgentError("Gemini vision supports JPEG, PNG, or WebP images.")

    model = _config_value(config, "GEMINI_VISION_MODEL", DEFAULT_GEMINI_MODEL)
    prompt = f"""
You are a cautious plant-health screening vision model. Analyze the attached image only.
The user's selected crop context is {selected_crop!r}; do not assume it is correct if visual
evidence differs. Do not invent symptoms not visible in the image. Distinguish unknown,
healthy, disease symptoms, and pest damage. Use only a disease name supported by visible
evidence; otherwise say "uncertain" and lower confidence. Do not present this as a confirmed
laboratory diagnosis. Reply only as JSON with exactly these fields:
{{"detected_crop":"string","health_status":"healthy|diseased|pest damage|unknown",
"primary_diagnosis":"string","visual_symptoms":["short observable symptom",...],
"confidence_score":0.0}}
Confidence is a subjective visual screening score, not a calibrated probability.
Write symptom descriptions in {language}.
"""
    payload = _request_json(
        "POST",
        GEMINI_API_URL.format(model=model),
        timeout=float(config.get("AGENT_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
        headers={"x-goog-api-key": api_key},
        json={
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {
                        "mime_type": mime_type,
                        "data": base64.b64encode(image_bytes).decode("ascii"),
                    }},
                ],
            }],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "maxOutputTokens": 900,
            },
        },
    )
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as error:
        raise AgentError("Gemini did not return a vision assessment.") from error
    fields = _validate_vision_payload(_parse_json_object(text, "Gemini"))
    return VisionResult(*fields, provider=model)


def _local_fallback(local_vision: LocalVision) -> LocalResult:
    try:
        raw = local_vision()
    except Exception as error:
        return LocalResult(available=False, error=f"Local ONNX inference failed: {error}")
    try:
        confidence = float(raw.get("confidence_score", 0.0))
        margin = float(raw.get("confidence_margin", 0.0))
        if not 0.0 <= confidence <= 1.0 or not 0.0 <= margin <= 1.0:
            raise ValueError("Local model scores must be between 0 and 1.")
        supplied_metadata = raw.get("metadata", {})
        if not isinstance(supplied_metadata, Mapping):
            raise ValueError("Local model metadata must be a mapping.")
        metadata = dict(supplied_metadata)
        metadata.update({
            key: value for key, value in raw.items()
            if key not in {
                "available", "detected_crop", "primary_diagnosis",
                "confidence_score", "confidence_margin", "health_status",
                "provider", "error", "metadata",
            }
        })
        return LocalResult(
            available=bool(raw.get("available", True)),
            detected_crop=str(raw.get("detected_crop", "")),
            primary_diagnosis=str(raw.get("primary_diagnosis", "")),
            confidence_score=confidence,
            confidence_margin=margin,
            health_status=str(raw.get("health_status", "unknown")),
            provider=str(raw.get("provider", "local ONNX")),
            metadata=metadata,
        )
    except (TypeError, ValueError) as error:
        return LocalResult(available=False, error=f"Local ONNX output was invalid: {error}")


def _google_search(
    selected_crop: str,
    region: str,
    diagnosis_hint: str,
    config: Mapping[str, Any],
) -> SearchResult:
    api_key = _config_value(config, "GOOGLE_CSE_API_KEY")
    search_engine_id = _config_value(config, "GOOGLE_CSE_ID")
    if not api_key or not search_engine_id:
        return SearchResult(available=False)
    query = " ".join(
        part for part in (
            selected_crop,
            diagnosis_hint if diagnosis_hint else "crop disease pest alert",
            region,
            "agriculture extension alert",
        ) if part
    )
    try:
        payload = _request_json(
            "GET",
            "https://www.googleapis.com/customsearch/v1",
            timeout=float(config.get("AGENT_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
            params={"key": api_key, "cx": search_engine_id, "q": query, "num": MAX_SEARCH_RESULTS},
        )
    except AgentError as error:
        return SearchResult(available=False, message="Live regional search is unavailable.", error=str(error))
    items = payload.get("items", [])
    if not isinstance(items, list):
        return SearchResult(available=False, message="Search returned an unexpected result format.")
    results: list[dict[str, str]] = []
    for item in items[:MAX_SEARCH_RESULTS]:
        if not isinstance(item, dict):
            continue
        link = item.get("link")
        title = item.get("title")
        snippet = item.get("snippet")
        if not all(isinstance(value, str) for value in (link, title, snippet)):
            continue
        if urlparse(link).scheme not in {"https", "http"}:
            continue
        results.append({"title": title[:200], "url": link[:1000], "snippet": snippet[:700]})
    return SearchResult(
        available=bool(results),
        results=results,
        message="Regional web results retrieved; verify dates and guidance with the source." if results
        else "No regional extension search results were found.",
    )


def _candidate_diseases(crop_name: str) -> list[dict[str, str]]:
    family = _crop_family(crop_name)
    return [
        {"key": key, "name": entry["name"][0], "signs": entry["signs"][0][:700]}
        for key, entry in disease_data.DISEASES.items()
        if family and (not entry.get("crops") or family in entry["crops"])
        and entry.get("kind") != "healthy"
    ][:80]


def _ollama_reasoning(
    vision: VisionResult,
    local: LocalResult,
    config: Mapping[str, Any],
) -> ReasoningResult:
    model = _config_value(config, "OLLAMA_MODEL")
    if not model:
        return _knowledge_reasoning(vision, local)
    base_url = _config_value(config, "OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    if urlparse(base_url).scheme != "http" or urlparse(base_url).hostname not in {
        "127.0.0.1", "localhost", "::1",
    }:
        return ReasoningResult(
            supported=None,
            explanation="Ollama is restricted to a local endpoint; using deterministic knowledge-base checks.",
            provider="knowledge-base cross-check",
            error="OLLAMA_BASE_URL must point to localhost.",
        )
    prompt = {
        "instruction": (
            "Cross-examine this plant screening hypothesis against only the supplied crop "
            "disease candidates and visual symptoms. Do not diagnose beyond evidence. "
            "Return JSON {supported:boolean, explanation:string, alternatives:[string]}."
        ),
        "selected_crop": vision.detected_crop,
        "diagnosis": vision.primary_diagnosis,
        "symptoms": vision.visual_symptoms,
        "local_model_candidate": local.primary_diagnosis if local.available else "",
        "candidates": _candidate_diseases(vision.detected_crop),
    }
    try:
        response = _request_json(
            "POST",
            f"{base_url}/api/generate",
            timeout=float(config.get("AGENT_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
            json={"model": model, "prompt": json.dumps(prompt), "stream": False, "format": "json"},
        )
        output = _parse_json_object(response.get("response"), "Ollama")
        supported_value = output.get("supported")
        if not isinstance(supported_value, bool):
            raise AgentError("Ollama response lacks a boolean 'supported' value.")
        explanation = output.get("explanation")
        alternatives = output.get("alternatives", [])
        return ReasoningResult(
            supported=supported_value,
            explanation=str(explanation)[:1000] if isinstance(explanation, str) else "",
            alternatives=[item[:200] for item in alternatives[:5] if isinstance(item, str)]
            if isinstance(alternatives, list) else [],
            provider=f"Ollama ({model})",
        )
    except AgentError as error:
        fallback = _knowledge_reasoning(vision, local)
        return ReasoningResult(
            supported=fallback.supported,
            explanation=fallback.explanation,
            alternatives=fallback.alternatives,
            error=str(error),
        )


def _knowledge_reasoning(vision: VisionResult, local: LocalResult) -> ReasoningResult:
    key = _disease_key(vision.detected_crop, vision.primary_diagnosis)
    if vision.health_status == "healthy":
        return ReasoningResult(
            supported=vision.primary_diagnosis.casefold() in {"healthy", "no disease", "none"},
            explanation="Healthy classification is not proof that the plant is disease-free.",
        )
    if not key:
        return ReasoningResult(
            supported=None,
            explanation="The hypothesis did not map unambiguously to a crop-compatible knowledge-base entry.",
            alternatives=[item["name"] for item in _candidate_diseases(vision.detected_crop)[:4]],
        )
    entry = disease_data.DISEASES[key]
    family = _crop_family(vision.detected_crop)
    if entry.get("crops") and family not in entry["crops"]:
        return ReasoningResult(
            supported=False,
            explanation="The candidate is not listed for the visually selected crop family.",
        )
    local_key = _disease_key(local.detected_crop or vision.detected_crop, local.primary_diagnosis) if local.available else None
    alternatives = []
    if local_key and local_key != key:
        local_entry = disease_data.DISEASES.get(local_key, {})
        alternatives.append(local_entry.get("name", (local.primary_diagnosis,))[0])
    alternative_keys = entry.get("extra", {}).get("confusable_with", [])
    for alternative in alternative_keys:
        alternative_entry = disease_data.DISEASES.get(alternative, {})
        if alternative_entry:
            alternatives.append(alternative_entry["name"][0])
    supported = local_key == key if local_key else True
    explanation = (
        "The candidate maps to a crop-compatible knowledge-base entry."
        if supported else
        "The local ONNX candidate disagrees with Gemini; treat this result as uncertain."
    )
    return ReasoningResult(
        supported=supported,
        explanation=explanation,
        alternatives=list(dict.fromkeys(alternatives))[:5],
    )


def _make_local_vision_compat(local: LocalResult, selected_crop: str) -> VisionResult:
    if not local.available:
        return VisionResult(
            detected_crop=selected_crop,
            health_status="unknown",
            primary_diagnosis="uncertain",
            visual_symptoms=[],
            confidence_score=0.0,
            provider="unavailable",
            error=local.error,
        )
    return VisionResult(
        detected_crop=local.detected_crop or selected_crop,
        health_status=local.health_status,
        primary_diagnosis=local.primary_diagnosis or "uncertain",
        visual_symptoms=[],
        confidence_score=local.confidence_score,
        provider=local.provider,
        error=local.error,
    )


def _arbitrate(
    vision: VisionResult,
    local: LocalResult,
    reasoning: ReasoningResult,
    search: SearchResult,
    selected_crop: str,
    region: str,
) -> ConsensusReport:
    notes: list[str] = [
        "This is an AI screening aid, not a laboratory diagnosis.",
        "The consensus index is heuristic and is not a calibrated probability.",
    ]
    if vision.error:
        notes.append(f"Gemini vision was unavailable: {vision.error}")
    if local.error:
        notes.append(local.error)
    if reasoning.error:
        notes.append(f"Secondary reasoning fallback: {reasoning.error}")
    if not search.available:
        notes.append(search.message)
    if search.results:
        notes.append("Web search snippets are unverified; open the source and check publication dates.")

    disease_key = _disease_key(vision.detected_crop or selected_crop, vision.primary_diagnosis)
    local_key = _disease_key(local.detected_crop or selected_crop, local.primary_diagnosis) if local.available else None
    vision_available = vision.error is None and vision.confidence_score > 0
    if vision_available:
        final_diagnosis = vision.primary_diagnosis
        final_crop = vision.detected_crop or selected_crop
        base_score = vision.confidence_score
        if local.available:
            if disease_key and disease_key == local_key:
                base_score = 0.65 * base_score + 0.35 * local.confidence_score
                agreement = "Gemini and local ONNX agree"
            elif disease_key and local_key:
                base_score *= 0.75
                agreement = "Gemini and local ONNX disagree"
                notes.append(f"Local ONNX alternative: {local.primary_diagnosis}.")
            else:
                agreement = "Gemini result has no matching local disease candidate"
        else:
            agreement = "Gemini only; local ONNX was unavailable or unsupported for this crop"
    elif local.available:
        final_diagnosis = local.primary_diagnosis
        final_crop = local.detected_crop or selected_crop
        base_score = min(local.confidence_score, 0.60)
        agreement = "Local ONNX fallback; Gemini vision unavailable"
        disease_key = local_key
    else:
        final_diagnosis = "Uncertain — no vision agent returned a usable candidate"
        final_crop = selected_crop
        base_score = 0.0
        agreement = "No usable vision result"

    if reasoning.supported is False:
        base_score *= 0.65
        notes.append("Secondary cross-check did not support the leading hypothesis.")
    elif reasoning.supported is True:
        base_score = min(1.0, base_score + 0.05)
    if not disease_key and final_diagnosis.casefold() not in {"healthy", "no disease", "none"}:
        notes.append("No unambiguous crop-compatible knowledge-base mapping was found.")
    confidence_index = round(max(0.0, min(1.0, base_score)) * 100, 1)
    status = vision.health_status if vision_available else (
        local.health_status if local.available else "unknown"
    )
    return ConsensusReport(
        detected_crop=final_crop,
        health_status=status,
        primary_diagnosis=final_diagnosis,
        disease_key=disease_key,
        visual_symptoms=vision.visual_symptoms if vision_available else [],
        consensus_confidence_index=confidence_index,
        confidence_is_calibrated=False,
        agreement=agreement,
        vision=vision,
        local_vision=local,
        reasoning=reasoning,
        web_grounding=search,
        region=region,
        notes=notes,
    )


def run_consensus(
    image_bytes: bytes,
    mime_type: str,
    selected_crop: str,
    region: str,
    language: str,
    local_vision: LocalVision,
    *,
    config: Mapping[str, Any] | None = None,
    progress: ProgressCallback | None = None,
) -> ConsensusReport:
    """Run vision, local inference, and regional search concurrently.

    Local ONNX inference is started in parallel with Gemini so the app has an
    immediate fallback if the remote request fails. The reasoning agent runs
    after vision results arrive because it needs those symptoms and hypotheses.
    """
    settings = config or {}
    if not image_bytes:
        raise ValueError("Image bytes must not be empty.")
    if not selected_crop.strip() or not region.strip():
        raise ValueError("Crop context and region are required.")

    def update(stage: str, message: str) -> None:
        if progress:
            progress(stage, message)

    update("starting", "Starting vision, local fallback, and regional search agents.")
    agent_timeout = float(settings.get("AGENT_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="cropguard-agent")
    local_future = executor.submit(_local_fallback, local_vision)

    def search_with_local_context() -> SearchResult:
        diagnosis_hint = ""
        try:
            local_candidate = local_future.result(timeout=min(agent_timeout, 5.0))
            if (
                local_candidate.available
                and local_candidate.health_status != "healthy"
                and local_candidate.metadata.get("diagnosis_available") is not False
            ):
                diagnosis_hint = local_candidate.primary_diagnosis
        except TimeoutError:
            pass
        return _google_search(selected_crop, region, diagnosis_hint, settings)

    futures: dict[Future[Any], str] = {
        executor.submit(_gemini_vision, image_bytes, mime_type, selected_crop, language, settings): "vision",
        local_future: "local",
        executor.submit(search_with_local_context): "search",
    }
    results: dict[str, Any] = {}
    try:
        for future in as_completed(futures, timeout=agent_timeout + 2):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as error:
                if name == "vision":
                    results[name] = VisionResult(
                        detected_crop=selected_crop,
                        health_status="unknown",
                        primary_diagnosis="uncertain",
                        visual_symptoms=[],
                        confidence_score=0.0,
                        provider="Gemini unavailable",
                        error=str(error),
                    )
                elif name == "local":
                    results[name] = LocalResult(available=False, error=str(error))
                else:
                    results[name] = SearchResult(
                        available=False,
                        message="Live regional search is unavailable.",
                        error=str(error),
                    )
            update(name, f"{name.title()} agent completed.")
    except TimeoutError:
        for future, name in futures.items():
            if future.done() or name in results:
                continue
            future.cancel()
            error = f"{name.title()} agent exceeded its {agent_timeout:g} second timeout."
            if name == "vision":
                results[name] = VisionResult(
                    selected_crop, "unknown", "uncertain", [], 0.0, "Gemini timed out", error
                )
            elif name == "local":
                results[name] = LocalResult(available=False, error=error)
            else:
                results[name] = SearchResult(available=False, message=error, error=error)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    vision: VisionResult = results.get("vision") or VisionResult(
        selected_crop, "unknown", "uncertain", [], 0.0, "Gemini unavailable",
        "Gemini vision did not complete before the timeout.",
    )
    local: LocalResult = results.get("local") or LocalResult(
        available=False, error="Local ONNX inference did not complete before the timeout."
    )
    search: SearchResult = results.get("search") or SearchResult(
        available=False, message="Live regional search did not complete before the timeout."
    )
    if vision.error and local.available:
        vision = _make_local_vision_compat(local, selected_crop)
        vision = VisionResult(
            detected_crop=vision.detected_crop,
            health_status=vision.health_status,
            primary_diagnosis=vision.primary_diagnosis,
            visual_symptoms=vision.visual_symptoms,
            confidence_score=vision.confidence_score,
            provider=vision.provider,
            error=results["vision"].error if "vision" in results else "Gemini unavailable",
        )
    update("reasoning", "Cross-checking symptoms and candidate against crop knowledge.")
    reasoning = _ollama_reasoning(vision, local, settings)
    update("arbitration", "Synthesizing candidate agreement and confidence index.")
    return _arbitrate(vision, local, reasoning, search, selected_crop, region)
