from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from collections import defaultdict

router = APIRouter(prefix="/api/labs", tags=["labs"])


class LabItem(BaseModel):
    itemid: int
    lab_name: str
    fluid: str


def get_lab_dictionary(request: Request) -> list[dict]:
    return request.app.state.lab_dictionary


@router.get("", response_model=dict[str, list[LabItem]])
def list_labs(lab_dictionary: list[dict] = Depends(get_lab_dictionary)):
    """Return all labs from d_labitems grouped by category."""
    grouped: dict[str, list[LabItem]] = defaultdict(list)
    for lab in lab_dictionary:
        category = lab.get("category") or "Uncategorized"
        grouped[category].append(
            LabItem(
                itemid=lab["itemid"],
                lab_name=lab["lab_name"],
                fluid=lab["fluid"],
            )
        )
    return dict(grouped)
