"""
Pydantic schemas for polymorphic target entity references.

Provides shared types for the polymorphic target pattern used by
Job and AnalysisResult models (Issue #110).
"""

from typing import Optional
from pydantic import BaseModel, Field
from backend.src.models import TargetEntityType


class TargetEntityInfo(BaseModel):
    """Primary target entity for a Job or AnalysisResult."""
    entity_type: TargetEntityType
    entity_guid: str = Field(..., description="Target entity GUID (col_xxx, con_xxx, pip_xxx, cam_xxx)")
    entity_name: Optional[str] = Field(None, description="Cached display name of the target entity")


class ContextEntityRef(BaseModel):
    """Snapshot reference to a related entity in context."""
    guid: str = Field(..., description="Entity GUID")
    name: Optional[str] = Field(None, description="Entity name at time of execution")


class PipelineContextRef(ContextEntityRef):
    """Pipeline reference with version snapshot."""
    version: Optional[int] = Field(None, description="Pipeline version at time of execution")


class ResultContext(BaseModel):
    """Execution context — secondary entity references."""
    pipeline: Optional[PipelineContextRef] = None
    connector: Optional[ContextEntityRef] = None
