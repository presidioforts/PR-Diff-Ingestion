"""Pydantic models for P1 Diff API requests and responses."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class DiffRequest(BaseModel):
    """Request model for diff endpoint."""
    
    repo_url: str = Field(
        ...,
        description="Repository URL (https/http) or local path",
        example="https://github.com/user/repo.git"
    )
    commit_good: str = Field(
        ...,
        description="Good commit SHA (baseline)",
        example="ba7765dd48c0ba51f4fd12cde48fd100aecdb743"
    )
    commit_candidate: str = Field(
        ...,
        description="Candidate commit SHA (comparison target)",
        example="d7a39abec5a282b9955afdd1649a5f1bafae35f7"
    )
    branch_name: Optional[str] = Field(
        None,
        description="Branch name for context and fetch hint",
        example="feature/new-feature"
    )
    cap_total: int = Field(
        800000,
        description="Total capacity limit in bytes",
        ge=1000,
        le=10000000
    )
    cap_file: int = Field(
        64000,
        description="Per-file capacity limit in bytes",
        ge=100,
        le=1000000
    )
    context_lines: int = Field(
        3,
        description="Number of context lines in diffs",
        ge=0,
        le=10
    )
    find_renames_threshold: int = Field(
        90,
        description="Rename detection threshold percentage",
        ge=0,
        le=100
    )
    
    @field_validator('cap_file')
    @classmethod
    def cap_file_must_not_exceed_cap_total(cls, v, info):
        """Validate that cap_file doesn't exceed cap_total."""
        if info.data and 'cap_total' in info.data and v > info.data['cap_total']:
            raise ValueError('cap_file cannot exceed cap_total')
        return v
    
    @field_validator('repo_url')
    @classmethod
    def repo_url_must_be_valid(cls, v):
        """Basic validation for repository URL."""
        v = v.strip()
        if not v:
            raise ValueError('repo_url cannot be empty')
        # Allow both URLs and local paths
        if not (v.startswith(('http://', 'https://')) or v.startswith('/') or (len(v) > 2 and v[1] == ':')):
            raise ValueError('repo_url must be a valid URL or absolute path')
        return v
    
    @field_validator('commit_good', 'commit_candidate')
    @classmethod
    def commit_sha_must_be_valid(cls, v):
        """Basic validation for commit SHAs."""
        v = v.strip()
        if not v:
            raise ValueError('commit SHA cannot be empty')
        if len(v) < 7:
            raise ValueError('commit SHA must be at least 7 characters')
        return v


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(..., example="healthy")
    version: str = Field(..., example="1.0.0")
    git_available: bool = Field(..., example=True)
    git_version: Optional[str] = Field(None, example="2.34.1")


class VersionResponse(BaseModel):
    """Response model for version endpoint."""
    
    version: str = Field(..., example="1.0.0")
    api_version: str = Field(..., example="v1")
    git_version: Optional[str] = Field(None, example="2.34.1")
    supported_features: list = Field(
        default_factory=lambda: [
            "deterministic_output",
            "capacity_management", 
            "rename_detection",
            "binary_detection",
            "submodule_detection"
        ]
    )
