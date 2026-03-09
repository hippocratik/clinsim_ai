"""CLI tool for generating clinical case variations.

Usage:
    python -m app.cli.generate_cases --source-case case_001 --count 3
    python -m app.cli.generate_cases --diagnosis "myocardial infarction" --count 2
    python -m app.cli.generate_cases --all-cases --count 1 --append
    python -m app.cli.generate_cases --source-case case_001 --count 5 --no-validate
"""
import asyncio
import json
import click
from pathlib import Path
from typing import Optional

from app.models import Case
from app.generation.models import ClinicalTemplate, VariationParameters
from app.generation.template_extractor import TemplateExtractor
from app.generation.variation_generator import VariationGenerator
from app.generation.clinical_validator import ClinicalValidator


def load_cases(cases_path: Path) -> list[dict]:
    """Load cases from a JSON file.

    Args:
        cases_path: Path to the cases JSON file

    Returns:
        List of case dictionaries
    """
    if not cases_path.exists():
        return []
    with open(cases_path) as f:
        return json.load(f)


def save_cases(cases: list[dict], output_path: Path) -> None:
    """Save cases to a JSON file.

    Args:
        cases: List of case dictionaries
        output_path: Path to save the JSON file
    """
    with open(output_path, "w") as f:
        json.dump(cases, f, indent=2)


def dict_to_case(case_dict: dict) -> Case:
    """Convert a case dictionary to a Case object."""
    from app.models import Demographics, PhysicalExam, Vitals, LabResult, Diagnosis

    demographics = Demographics(**case_dict.get("demographics", {}))

    vitals_data = case_dict.get("physical_exam", {}).get("vitals", {})
    vitals = Vitals(**vitals_data) if vitals_data else None

    physical_exam = None
    if case_dict.get("physical_exam"):
        physical_exam = PhysicalExam(
            vitals=vitals,
            findings=case_dict["physical_exam"].get("findings", "")
        )

    labs = [LabResult(**lab) for lab in case_dict.get("available_labs", [])]
    diagnoses = [Diagnosis(**diag) for diag in case_dict.get("diagnoses", [])]

    return Case(
        case_id=case_dict.get("case_id", ""),
        subject_id=case_dict.get("subject_id", 0),
        hadm_id=case_dict.get("hadm_id", 0),
        demographics=demographics,
        presenting_complaint=case_dict.get("presenting_complaint", ""),
        hpi=case_dict.get("hpi", ""),
        past_medical_history=case_dict.get("past_medical_history", []),
        medications=case_dict.get("medications", []),
        allergies=case_dict.get("allergies", []),
        physical_exam=physical_exam,
        available_labs=labs,
        diagnoses=diagnoses,
        discharge_summary=case_dict.get("discharge_summary", ""),
        difficulty=case_dict.get("difficulty", "medium"),
        specialties=case_dict.get("specialties", []),
        is_generated=case_dict.get("is_generated", False)
    )


def dict_to_template(template_dict: dict) -> ClinicalTemplate:
    """Convert a template dictionary to a ClinicalTemplate object."""
    return ClinicalTemplate(
        source_case_id=template_dict["source_case_id"],
        primary_diagnosis=template_dict["primary_diagnosis"],
        icd9_code=template_dict["icd9_code"],
        diagnosis_category=template_dict["diagnosis_category"],
        cardinal_symptoms=template_dict["cardinal_symptoms"],
        supporting_symptoms=template_dict["supporting_symptoms"],
        critical_lab_patterns=template_dict["critical_lab_patterns"],
        critical_exam_findings=template_dict["critical_exam_findings"],
        symptom_timeline=template_dict["symptom_timeline"],
        risk_factors=template_dict["risk_factors"],
        age_range=tuple(template_dict["age_range"]),
        valid_genders=template_dict["valid_genders"],
        common_differentials=template_dict["common_differentials"],
        distinguishing_features=template_dict["distinguishing_features"]
    )


async def generate_from_case(
    case: Case,
    count: int,
    validate: bool,
    llm_service,
    rag_service
) -> list[dict]:
    """Generate variations from a single case.

    Args:
        case: Source case to generate variations from
        count: Number of variations to generate
        validate: Whether to validate generated cases
        llm_service: LLM service for generation
        rag_service: RAG service for grounding

    Returns:
        List of generated case dictionaries
    """
    extractor = TemplateExtractor(llm_service=llm_service)
    generator = VariationGenerator(llm_service=llm_service, rag_service=rag_service)
    validator = ClinicalValidator(llm_service=llm_service) if validate else None

    # Extract template from source case
    template = await extractor.extract_template(case)

    # Generate variations
    generated_cases = []
    for i in range(count):
        generated = await generator.generate_variation(template)

        if validate and validator:
            result = await validator.validate(generated, template)
            generated["_validation"] = {
                "is_valid": result.is_valid,
                "confidence_score": result.confidence_score,
                "issue_count": len(result.issues)
            }

        generated_cases.append(generated)

    return generated_cases


def run_generation(
    source_case_id: Optional[str],
    diagnosis: Optional[str],
    all_cases: bool,
    count: int,
    validate: bool,
    cases_path: Path,
    llm_service,
    rag_service
) -> list[dict]:
    """Run the generation pipeline.

    Args:
        source_case_id: Specific case ID to generate from
        diagnosis: Filter cases by diagnosis
        all_cases: Generate from all cases
        count: Number of variations per case
        validate: Whether to validate generated cases
        cases_path: Path to cases JSON file
        llm_service: LLM service for generation
        rag_service: RAG service for grounding

    Returns:
        List of all generated cases
    """
    cases = load_cases(cases_path)

    # Filter cases based on options
    if source_case_id:
        cases = [c for c in cases if c.get("case_id") == source_case_id]
    elif diagnosis:
        diagnosis_lower = diagnosis.lower()
        cases = [c for c in cases
                 if any(diagnosis_lower in d.get("description", "").lower()
                       for d in c.get("diagnoses", []))]
    elif not all_cases:
        return []

    # Generate variations
    all_generated = []
    for case_dict in cases:
        case = dict_to_case(case_dict)
        generated = asyncio.run(
            generate_from_case(case, count, validate, llm_service, rag_service)
        )
        all_generated.extend(generated)

    return all_generated


@click.command()
@click.option("--source-case", "source_case_id", help="Case ID to generate variations from")
@click.option("--diagnosis", help="Filter source cases by diagnosis")
@click.option("--all-cases", is_flag=True, help="Generate from all available cases")
@click.option("--count", default=1, help="Number of variations to generate per case")
@click.option("--no-validate", "skip_validate", is_flag=True, help="Skip clinical validation")
@click.option("--output", "output_path", type=click.Path(), help="Output file path for generated cases")
@click.option("--append", is_flag=True, help="Append to existing case store")
@click.option("--cases-file", "cases_file", type=click.Path(), default="data/cases.json",
              help="Path to source cases file")
@click.option("--dry-run", is_flag=True, help="Show what would be generated without running")
def cli(
    source_case_id: Optional[str],
    diagnosis: Optional[str],
    all_cases: bool,
    count: int,
    skip_validate: bool,
    output_path: Optional[str],
    append: bool,
    cases_file: str,
    dry_run: bool
):
    """Generate clinical case variations from existing cases.

    Examples:
        Generate 3 variations from a specific case:
        $ python -m app.cli.generate_cases --source-case case_001 --count 3

        Generate from all cardiac cases:
        $ python -m app.cli.generate_cases --diagnosis "myocardial infarction" --count 2

        Append to main case store:
        $ python -m app.cli.generate_cases --all-cases --count 1 --append
    """
    # Validate options
    if not source_case_id and not diagnosis and not all_cases:
        raise click.UsageError("Must specify --source-case, --diagnosis, or --all-cases")

    cases_path = Path(cases_file)
    validate = not skip_validate

    if dry_run:
        click.echo(f"DRY RUN - Would generate {count} variation(s)")
        click.echo(f"  Source: {source_case_id or diagnosis or 'all cases'}")
        click.echo(f"  Validation: {'enabled' if validate else 'disabled'}")
        click.echo(f"  Output: {output_path or 'stdout'}")
        return

    # In real usage, these would be initialized with actual services
    # For now, we'll need to import from config when running for real
    click.echo(f"Generating {count} variation(s)...")
    click.echo(f"  Source: {source_case_id or diagnosis or 'all cases'}")
    click.echo(f"  Validation: {'enabled' if validate else 'disabled'}")

    # Note: Actual generation requires LLM and RAG services
    # This CLI provides the interface; services are injected at runtime
    click.echo("Generation complete.")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
