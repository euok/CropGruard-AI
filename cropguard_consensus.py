"""Cost-conscious diagnostic consensus for CropGuard AI.

Gemini vision runs alongside local ONNX inference and optional Google Custom
Search. A configured local Ollama model then checks Gemini's hypothesis. Scores
are heuristic screening signals, not calibrated probabilities.
"""

from __future__ import annotations

import json
import os
import re
import traceback
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from google import genai
from google.genai import types
import requests

import disease_data


LocalVision = Callable[[], Mapping[str, Any]]
ProgressCallback = Callable[[str, str], None]

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
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
    image_quality: str = ""


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
    message: str = "Regional search has not been requested."
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


class ProviderError(AgentError):
    """A provider failure that allows the consensus engine to use another agent."""


def _config_value(config: Mapping[str, Any], key: str, default: str = "") -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        value = os.environ.get(key, default)
    return value.strip() if isinstance(value, str) else default


def _generate_gemini_content(
    client: Any,
    model: str,
    contents: Any,
    generation_config: Any,
) -> tuple[Any, str]:
    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generation_config,
        )
    except Exception as error:
        print(f"Gemini API Error: {error}")
        traceback.print_exc()
        raise ProviderError(f"Gemini request failed for {model}: {error}") from error
    return response, model


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


def extract_json(value: Any, agent_name: str) -> dict[str, Any]:
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
        raise AgentError(
            f"{agent_name} returned invalid JSON at line {error.lineno}, "
            f"column {error.colno}: {error.msg}."
        ) from error
    if not isinstance(result, dict):
        raise AgentError(f"{agent_name} returned JSON that was not an object.")
    return result


def _validate_vision_payload(
    payload: Mapping[str, Any],
) -> tuple[str, str, str, list[str], float, str]:
    crop = payload.get("detected_crop")
    status = payload.get("health_status")
    diagnosis = payload.get("primary_diagnosis")
    symptoms = payload.get("visual_symptoms")
    confidence = payload.get("confidence", payload.get("confidence_score"))
    image_quality = payload.get("image_quality", "")
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
    if not isinstance(image_quality, str):
        image_quality = ""
    return (
        crop.strip(),
        status,
        diagnosis.strip(),
        symptoms[:12],
        confidence_number,
        image_quality.strip(),
    )


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
        raise ProviderError("Gemini image request exceeds the 15 MB limit; local ONNX fallback remains available.")
    api_key = _config_value(config, "GEMINI_API_KEY")
    if not api_key:
        raise ProviderError(
            "Gemini vision requires GEMINI_API_KEY in the environment or Streamlit secrets; "
            "local vision will be used."
        )
    if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
        raise ProviderError("The uploaded image is empty or exceeds the 15 MB limit.")
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ProviderError("Gemini vision supports JPEG, PNG, or WebP images.")

    crop_family = _crop_family(selected_crop) or "unknown"
    prompt = f"""
You are a cautious plant-pathology screening model. Examine only the attached image for
visible evidence. The selected crop is {selected_crop!r}, in the {crop_family!r} family.
Treat these as context, not proof; report a different crop if the image supports it. Describe
only observable symptoms. Distinguish healthy plants, disease symptoms, pest damage, and
uncertain cases. Use a disease name only when supported by visible evidence; otherwise report
"uncertain" and lower confidence. This is a screening aid, not a laboratory diagnosis.
Assess whether image quality (focus, lighting, and visible leaf area) limits diagnosis.
Reply only as JSON with exactly these fields:
{{"detected_crop":"string","health_status":"healthy|diseased|pest damage|unknown",
"primary_diagnosis":"string","visual_symptoms":["short observable symptom"],
"confidence":0.0,"image_quality":"short description"}}
Confidence is a subjective score from 0 to 1, not a calibrated probability.
Write symptom descriptions in {language}.
Do not name an AI provider or model; present findings as CropGuard screening results.
"""
    try:
        client = genai.Client(api_key=api_key)
    except Exception as error:
        print(f"Gemini client initialization error: {error}")
        traceback.print_exc()
        raise ProviderError(f"Gemini client initialization failed: {error}") from error

    try:
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    except Exception as error:
        print(f"Gemini image payload error: {error}")
        traceback.print_exc()
        raise ProviderError(f"Gemini could not prepare the image payload: {error}") from error

    model = _config_value(config, "GEMINI_CHAT_MODEL", DEFAULT_GEMINI_MODEL)
    response, _ = _generate_gemini_content(
        client,
        model,
        [prompt, image_part],
        types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            max_output_tokens=900,
        ),
    )
    try:
        response_text = response.text
    except Exception as error:
        print(f"Gemini response error: {error}")
        traceback.print_exc()
        raise ProviderError(f"Gemini response could not be read: {error}") from error
    if not isinstance(response_text, str) or not response_text.strip():
        raise ProviderError(f"{model} did not return a vision assessment.")
    try:
        fields = _validate_vision_payload(extract_json(response_text, model))
    except AgentError as error:
        raise ProviderError(str(error)) from error
    return VisionResult(*fields[:5], provider=model, image_quality=fields[5])


def generate_uncertain_diagnostic(
    image_bytes: bytes,
    mime_type: str,
    crop: str,
    region: str,
    language: str,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Ask Gemini for a cautious differential and visible-severity estimate."""
    api_key = _config_value(config, "GEMINI_API_KEY")
    if not api_key:
        raise ProviderError("Gemini gap assessment is unavailable because GEMINI_API_KEY is not configured.")
    if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
        raise ProviderError("Gemini gap assessment requires a non-empty image no larger than 15 MB.")
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ProviderError("Gemini gap assessment supports JPEG, PNG, or WebP images.")

    prompt = f"""
You are a cautious agricultural extension assistant reviewing a plant photo because the
initial screening could not provide a reliable diagnosis or visual estimate. Crop context:
{crop!r}. Region context: {region!r}. Respond in {language}.

Examine only what is visible in the image. Give the best-supported assessment, but do not
force a disease name. If evidence is ambiguous, say so and list up to three plausible
possibilities with brief reasons. Estimate the percentage of visible leaf area affected only
if a leaf is clearly visible and the estimate is meaningful; otherwise return null. This
percentage is a rough visual estimate, not disease severity or a calibrated measurement.
Do not recommend pesticides, products, dosages, or chemical treatments. Give only cautious,
low-risk next steps and say when an in-person agricultural extension assessment is needed.
Do not name an AI provider or model; present findings as CropGuard screening results.

Return only JSON with these fields:
{{"assessment":"string",
"confidence":0.0,
"visual_discoloration_percent":null,
"severity_description":"string",
"observations":["string"],
"next_steps":["string"],
"seek_help_when":"string",
"image_quality":"string"}}
Confidence is a subjective screening score from 0 to 1, not a calibrated probability.
"""
    try:
        client = genai.Client(api_key=api_key)
        model = _config_value(config, "GEMINI_CHAT_MODEL", DEFAULT_GEMINI_MODEL)
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        response, _ = _generate_gemini_content(
            client,
            model,
            [prompt, image_part],
            types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                max_output_tokens=900,
            ),
        )
        response_text = response.text
    except Exception as error:
        raise ProviderError(f"Gemini could not complete the gap assessment: {error}") from error

    try:
        result = extract_json(response_text, "Gemini gap assessment")
    except AgentError as error:
        raise ProviderError(str(error)) from error

    assessment = result.get("assessment")
    seek_help_when = result.get("seek_help_when")
    severity_description = result.get("severity_description")
    image_quality = result.get("image_quality")
    try:
        confidence = float(result.get("confidence"))
    except (TypeError, ValueError) as error:
        raise ProviderError("Gemini gap assessment did not include a valid confidence score.") from error
    if isinstance(result.get("confidence"), bool) or not 0.0 <= confidence <= 1.0:
        raise ProviderError("Gemini gap assessment confidence must be between 0 and 1.")
    if not isinstance(assessment, str) or not assessment.strip():
        raise ProviderError("Gemini gap assessment did not include a usable assessment.")
    if not isinstance(seek_help_when, str) or not seek_help_when.strip():
        raise ProviderError("Gemini gap assessment did not include escalation guidance.")
    if not isinstance(severity_description, str) or not isinstance(image_quality, str):
        raise ProviderError("Gemini gap assessment returned invalid severity or image-quality details.")
    if not image_quality.strip():
        raise ProviderError("Gemini gap assessment did not describe image quality.")
    severity_percent = result.get("visual_discoloration_percent")
    if severity_percent is not None:
        if isinstance(severity_percent, bool) or not isinstance(severity_percent, (int, float)):
            raise ProviderError("Gemini visual discoloration estimate must be a number or null.")
        if not 0 <= severity_percent <= 100:
            raise ProviderError("Gemini visual discoloration estimate must be between 0 and 100.")

    validated = {
        "assessment": assessment.strip()[:1200],
        "confidence": confidence,
        "visual_discoloration_percent": (
            float(severity_percent) if severity_percent is not None else None
        ),
        "severity_description": severity_description.strip()[:500],
        "seek_help_when": seek_help_when.strip()[:700],
        "image_quality": image_quality.strip()[:500],
    }
    for field_name in ("observations", "next_steps"):
        values = result.get(field_name)
        if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
            raise ProviderError(f"Gemini gap assessment field '{field_name}' must be a list of text.")
        validated[field_name] = [item.strip()[:500] for item in values[:8] if item.strip()]
    return validated


def generate_management_advisory(
    crop: str,
    diagnosis: str,
    symptoms: list[str],
    region: str,
    language: str,
    config: Mapping[str, Any],
    local_conditions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate farmer-facing management guidance and a cautious technical analysis."""
    api_key = _config_value(config, "GEMINI_API_KEY")
    if not api_key:
        raise ProviderError("Gemini guidance is unavailable because GEMINI_API_KEY is not configured.")

    prompt = f"""
You are CropGuard's cautious agricultural extension assistant. Provide brief, general,
practical crop-management guidance for this screening result, not a confirmed diagnosis.

Crop: {crop}
Screening candidate: {diagnosis}
Visible symptoms reported by the image screening model: {json.dumps(symptoms[:12])}
Region context: {region}
Available local conditions: {json.dumps(dict(local_conditions or {}), ensure_ascii=False)}
Respond in: {language}

Write a concise but useful farmer-friendly summary followed by a technical analysis.
Describe the common appearance of the suspected disease or stressor, but do not present
an uncertain screening candidate as confirmed. Make practical management steps ordered,
low-risk, and specific to the crop only when supported. Biological approaches may be
included only when broadly appropriate; do not invent a product or imply local approval.

Do not recommend pesticides, active ingredients, commercial products, application rates,
fertilizer rates, or local registrations: CropGuard will display any independently verified
country-and-crop-specific treatment guidance separately. If no such guidance is available,
say that approved treatments must be confirmed with the national agricultural authority or
a qualified extension officer. Never invent agro-vet names, addresses, contacts, phone
numbers, stock availability, or support hubs; CropGuard will append its configured regional
directory separately and users should verify details before travel or purchase.

For the technical analysis, state scientific classification only when the suspected cause
supports it. Distinguish fungal, bacterial, viral, oomycete, pest, and abiotic causes; do not
invent a species, strain, vector, spore pathway, or biochemical mechanism. Explain that
spores/vector dynamics do not apply to abiotic disorders or may be unknown when evidence is
insufficient. Describe mechanisms of action only at a general biological/agronomic level;
do not provide chemical action mechanisms or dosing. Clearly identify uncertainty and
missing evidence. Do not name an AI provider or model; present this as CropGuard guidance.

Return only a JSON object with these fields:
{{"disease_detected_description":"string",
"management_options":["string"],
"where_to_obtain_cures":"string",
"scientific_classification":"string",
"pathology_physiology":"string",
"environmental_dynamics":"string",
"mechanisms_of_action":"string",
"when_to_seek_help":"string"}}
Keep the farmer summary jargon-free and the technical analysis rigorous but readable.
Do not state unsupported specifics. Use an explicit uncertainty statement wherever facts
cannot be determined from the candidate, symptoms, crop, region, or supplied conditions.
"""
    try:
        client = genai.Client(api_key=api_key)
        model = _config_value(config, "GEMINI_CHAT_MODEL", DEFAULT_GEMINI_MODEL)
        response, _ = _generate_gemini_content(
            client,
            model,
            prompt,
            types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                max_output_tokens=1800,
            ),
        )
        response_text = response.text
    except Exception as error:
        raise ProviderError(f"Gemini could not generate management advice: {error}") from error

    try:
        result = extract_json(response_text, "Gemini advisory")
    except AgentError as error:
        raise ProviderError(str(error)) from error

    required_text_fields = (
        "disease_detected_description",
        "where_to_obtain_cures",
        "scientific_classification",
        "pathology_physiology",
        "environmental_dynamics",
        "mechanisms_of_action",
        "when_to_seek_help",
    )
    for field_name in required_text_fields:
        value = result.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ProviderError(
                f"Management advisory did not include usable {field_name} content."
            )
    management_options = result.get("management_options")
    if not isinstance(management_options, list) or any(
        not isinstance(item, str) for item in management_options
    ):
        raise ProviderError("Management options must be a list of text.")

    when_to_seek_help = result.get("when_to_seek_help")
    advisory = {
        field_name: result[field_name].strip()[:1800]
        for field_name in required_text_fields
    }
    advisory["management_options"] = [
        item.strip()[:700] for item in management_options[:12] if item.strip()
    ]
    return advisory


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
    api_key = _config_value(config, "SERPER_API_KEY")
    if not api_key:
        return SearchResult(
            available=False,
            message="Live regional search is not configured; missing SERPER_API_KEY.",
        )
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
            "POST",
            "https://google.serper.dev/search",
            timeout=float(config.get("AGENT_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            json={"q": query, "num": MAX_SEARCH_RESULTS},
        )
    except AgentError as error:
        safe_error = str(error).replace(api_key, "[redacted]")
        return SearchResult(
            available=False,
            message="Live regional search is unavailable because the Serper request failed.",
            error=safe_error,
        )
    except (TypeError, ValueError) as error:
        return SearchResult(
            available=False,
            message="Live regional search could not be completed because its configuration is invalid.",
            error=str(error).replace(api_key, "[redacted]"),
        )
    items = payload.get("organic", [])
    if not isinstance(items, list):
        return SearchResult(
            available=False,
            message="Serper returned an unexpected result format.",
        )
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
        else "Serper returned no regional extension search results.",
    )


def run_regional_search(
    selected_crop: str,
    region: str,
    diagnosis_hint: str,
    config: Mapping[str, Any],
) -> SearchResult:
    """Run one optional regional web search after the user requests it."""
    try:
        return _google_search(selected_crop, region, diagnosis_hint, config)
    except Exception as error:
        api_key = _config_value(config, "SERPER_API_KEY")
        safe_error = str(error).replace(api_key, "[redacted]") if api_key else str(error)
        return SearchResult(
            available=False,
            message="Live regional search could not be completed.",
            error=safe_error,
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
            "disease candidates and visual symptoms. Evaluate the Gemini hypothesis against "
            "the knowledge base independently. A different local ONNX candidate alone does "
            "not refute Gemini; report it only as an alternative. Do not diagnose beyond evidence. "
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
        output = extract_json(response.get("response"), "Ollama")
        supported_value = output.get("supported")
        if not isinstance(supported_value, bool):
            raise AgentError("Ollama response lacks a boolean 'supported' value.")
        explanation = output.get("explanation")
        alternatives = output.get("alternatives", [])
        gemini_key = _disease_key(vision.detected_crop, vision.primary_diagnosis)
        local_key = (
            _disease_key(local.detected_crop or vision.detected_crop, local.primary_diagnosis)
            if local.available else None
        )
        if supported_value is False and gemini_key and local_key and gemini_key != local_key:
            supported_value = None
            explanation = (
                f"{explanation or ''} The local ONNX disagreement is retained as an "
                "alternative and does not invalidate the Gemini hypothesis."
            )
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
    supported = None if local_key and local_key != key else True
    explanation = "The candidate maps to a crop-compatible knowledge-base entry."
    if local_key and local_key != key:
        explanation += (
            " Local ONNX proposed a different candidate; that disagreement is retained "
            "as an alternative and does not invalidate the Gemini hypothesis."
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
        notes.append("Image assessment was unavailable; any local fallback is identified below.")
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
                agreement = "Visual assessment and local model agree"
            elif disease_key and local_key:
                agreement = "Visual assessment and local model disagree"
                notes.append(f"Local ONNX alternative: {local.primary_diagnosis}.")
            else:
                agreement = "Visual assessment has no matching local disease candidate"
        else:
            agreement = "Visual assessment only; local model was unavailable or unsupported for this crop"
    elif local.available:
        final_diagnosis = local.primary_diagnosis
        final_crop = local.detected_crop or selected_crop
        base_score = min(local.confidence_score, 0.60)
        agreement = "Local model fallback; image assessment unavailable"
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
    """Run Gemini vision first, then local inference and regional search."""
    settings = config or {}
    if not image_bytes:
        raise ValueError("Image bytes must not be empty.")
    if not selected_crop.strip() or not region.strip():
        raise ValueError("Crop context and region are required.")

    def update(stage: str, message: str) -> None:
        if progress:
            progress(stage, message)

    update("starting", "Starting image screening.")
    update("vision", "Assessing the crop image.")
    try:
        vision = _gemini_vision(
            image_bytes, mime_type, selected_crop, language, settings
        )
    except Exception as error:
        vision = VisionResult(
            detected_crop=selected_crop,
            health_status="unknown",
            primary_diagnosis="uncertain",
            visual_symptoms=[],
            confidence_score=0.0,
            provider="Gemini unavailable",
            error=str(error),
        )
    update("vision", "Image assessment completed.")

    update("local", "Starting local model cross-check.")
    local = _local_fallback(local_vision)
    if vision.error and local.available:
        gemini_error = vision.error
        vision = _make_local_vision_compat(local, selected_crop)
        vision = VisionResult(
            detected_crop=vision.detected_crop,
            health_status=vision.health_status,
            primary_diagnosis=vision.primary_diagnosis,
            visual_symptoms=vision.visual_symptoms,
            confidence_score=vision.confidence_score,
            provider=vision.provider,
            error=gemini_error,
        )
    search = SearchResult(
        available=False,
        message="Regional search has not been requested.",
    )
    update("reasoning", "Cross-checking symptoms and candidate against crop knowledge.")
    reasoning = _ollama_reasoning(vision, local, settings)
    update("arbitration", "Synthesizing candidate agreement and confidence index.")
    return _arbitrate(vision, local, reasoning, search, selected_crop, region)
