import uuid
from typing import TYPE_CHECKING, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.dependencies import get_llm_service, get_rag_service_optional, get_case_index
from app.core.llm import LLMService
from app.models import Case

if TYPE_CHECKING:
    from app.core.rag import RAGService

router = APIRouter(prefix="/api/generate", tags=["generation"])

# NOTE: generation_jobs lives in app.state (set at startup in main.py).
# For true multi-worker support, replace with Redis or a shared store.


# ── Request / Response schemas ────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    source_case_id: str
    target_diagnosis: Optional[str] = None
    difficulty: Optional[str] = None  # "easy" | "medium" | "hard"
    count: int = Field(default=1, ge=1, le=10)


class GenerateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    generated_case_ids: list[str]
    error: Optional[str] = None


# ── Background task ───────────────────────────────────────────────────────────

async def run_generation(
    job_id: str,
    request: GenerateRequest,
    llm_service: LLMService,
    rag_service: "RAGService",
    case_index: dict,
    generation_jobs: dict,
    app_state,
):
    """Background task that runs the generation pipeline."""
    try:
        generation_jobs[job_id]["status"] = "running"

        from app.generation.template_extractor import TemplateExtractor
        from app.generation.variation_generator import VariationGenerator
        from app.generation.clinical_validator import ClinicalValidator
        from app.generation.models import VariationParameters

        # Get source case
        case_data = case_index.get(request.source_case_id)
        if not case_data:
            raise ValueError(f"Source case '{request.source_case_id}' not found")
        case = Case(**case_data)

        # Initialize services
        extractor = TemplateExtractor(llm_service=llm_service)
        generator = VariationGenerator(llm_service=llm_service, rag_service=rag_service)
        validator = ClinicalValidator()

        # Extract template from source case
        template = await extractor.extract_template(case)

        generated_ids = []

        for _ in range(request.count):
            # Build variation parameters if provided
            params = None
            if request.difficulty or request.target_diagnosis:
                from app.generation.models import VariationParameters
                params = VariationParameters(
                    symptom_severity=request.difficulty or "typical",
                )

            # Generate variation
            variation_dict = await generator.generate_variation(
                template=template,
                params=params,
            )

            # Validate clinical accuracy
            validation_result = await validator.validate(variation_dict, template)
            if validation_result.is_valid:
                case_id = variation_dict.get("case_id", str(uuid.uuid4()))
                variation_dict["case_id"] = case_id

                # Persist to in-memory case store so GET /api/cases/{id} works
                app_state.case_index[case_id] = variation_dict
                app_state.cases.append(variation_dict)

                generated_ids.append(case_id)

        generation_jobs[job_id]["status"] = "completed"
        generation_jobs[job_id]["generated_case_ids"] = generated_ids

    except Exception as e:
        generation_jobs[job_id]["status"] = "failed"
        generation_jobs[job_id]["error"] = str(e)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=GenerateResponse)
async def generate_case_variation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    llm_service: LLMService = Depends(get_llm_service),
    rag_service = Depends(get_rag_service_optional),
    case_index: dict = Depends(get_case_index),
):
    """
    Create a new case generation job.
    Returns a job_id immediately — poll GET /api/generate/{job_id} for status.
    """
    if rag_service is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "RAG service unavailable. Case generation requires RAG for grounding. "
                "Fix PyTorch/sentence-transformers on this machine (WinError 1114), "
                "or run the backend in an environment where torch can load."
            ),
        )
    job_id = str(uuid.uuid4())

    req.app.state.generation_jobs[job_id] = {
        "status": "pending",
        "generated_case_ids": [],
        "error": None,
    }

    background_tasks.add_task(
        run_generation,
        job_id,
        request,
        llm_service,
        rag_service,
        case_index,
        req.app.state.generation_jobs,
        req.app.state,
    )

    return GenerateResponse(job_id=job_id, status="pending")


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_generation_status(job_id: str, req: Request):
    """Poll the status of a generation job."""
    job = req.app.state.generation_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        generated_case_ids=job["generated_case_ids"],
        error=job.get("error"),
    )
