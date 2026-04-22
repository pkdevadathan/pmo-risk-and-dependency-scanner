from typing import Literal

from pydantic import BaseModel, Field


class RiskItem(BaseModel):
    title: str = Field(..., description="Short risk title")
    category: str = Field(..., description="One taxonomy category")
    description: str = Field(..., description="Why this is a risk, with evidence from sources")
    likelihood: Literal["Low", "Medium", "High"] = "Medium"
    impact: Literal["Low", "Medium", "High", "Critical"] = "Medium"
    suggested_owner_role: str = Field(
        default="",
        description="Role or function that should own mitigation (not a real name unless stated)",
    )
    mitigation_hint: str = Field(default="", description="Concrete next step")
    source_snippet: str = Field(
        default="",
        description="Short verbatim or paraphrased quote from the document bundle",
    )


class DependencyItem(BaseModel):
    predecessor: str = Field(..., description="Work package or team that must finish first")
    successor: str = Field(..., description="Downstream work blocked or delayed if predecessor slips")
    description: str = Field(..., description="Nature of the dependency")
    if_slipped_impact: str = Field(default="", description="What breaks if predecessor is late")


class AnalysisResult(BaseModel):
    executive_summary: str = Field(..., max_length=1200)
    risks: list[RiskItem] = Field(default_factory=list)
    dependencies: list[DependencyItem] = Field(default_factory=list)
    open_questions_for_pm: list[str] = Field(
        default_factory=list,
        description="Gaps where documents are silent; PM should clarify",
    )
