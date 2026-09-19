"""Knowledge domain models and relationship schemas."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Provenance(BaseModel):
    """Source provenance tracking where a fact was derived from."""
    file: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    method: str = Field(default="ast", description="'ast', 'filesystem', 'git', or 'llm'")


class RelationshipType(str, Enum):
    """Types of directed relationships in the knowledge graph."""
    CONTAINS = "CONTAINS"          # Project contains Package/Module, Module contains Class/Function
    IMPORTS = "IMPORTS"            # Module/File imports Module/Symbol/Dependency
    CALLS = "CALLS"                # Function calls Function/Method
    INHERITS = "INHERITS"          # Class inherits from Class
    IMPLEMENTS = "IMPLEMENTS"      # Class implements Interface/Protocol
    DEPENDS_ON = "DEPENDS_ON"      # Component depends on ExternalDependency
    MODIFIED_BY = "MODIFIED_BY"    # File/Component modified by GitCommit


class KnowledgeNodeType(str, Enum):
    """Types of entities in the knowledge graph."""
    PROJECT = "project"
    FILE = "file"
    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    EXTERNAL_DEPENDENCY = "external_dependency"
    GIT_COMMIT = "git_commit"


class KnowledgeNode(BaseModel):
    """Base model for any node in the knowledge layer."""
    id: str
    type: KnowledgeNodeType
    name: str
    is_deterministic: bool = Field(default=True, description="True if derived deterministically, False if LLM generated")
    source: Optional[Provenance] = None
    docstring: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProjectNode(KnowledgeNode):
    type: KnowledgeNodeType = KnowledgeNodeType.PROJECT
    version: Optional[str] = None
    languages: List[str] = Field(default_factory=list)


class FileNode(KnowledgeNode):
    type: KnowledgeNodeType = KnowledgeNodeType.FILE
    path: str
    extension: str
    size_bytes: int = 0
    line_count: int = 0
    language: Optional[str] = None


class PackageNode(KnowledgeNode):
    type: KnowledgeNodeType = KnowledgeNodeType.PACKAGE
    package_path: str


class ModuleNode(KnowledgeNode):
    type: KnowledgeNodeType = KnowledgeNodeType.MODULE
    module_path: str
    file_path: str


class ClassNode(KnowledgeNode):
    type: KnowledgeNodeType = KnowledgeNodeType.CLASS
    bases: List[str] = Field(default_factory=list)
    decorators: List[str] = Field(default_factory=list)


class FunctionNode(KnowledgeNode):
    type: KnowledgeNodeType = KnowledgeNodeType.FUNCTION
    signature: Optional[str] = None
    parameters: List[str] = Field(default_factory=list)
    return_type: Optional[str] = None
    is_async: bool = False
    decorators: List[str] = Field(default_factory=list)


class ExternalDependencyNode(KnowledgeNode):
    type: KnowledgeNodeType = KnowledgeNodeType.EXTERNAL_DEPENDENCY
    package_name: str
    version_spec: Optional[str] = None


class GitCommitNode(KnowledgeNode):
    type: KnowledgeNodeType = KnowledgeNodeType.GIT_COMMIT
    hexsha: str
    author_name: str
    committed_datetime: str
    message: str


class KnowledgeEdge(BaseModel):
    """Directed edge in the knowledge graph."""
    source_id: str
    target_id: str
    type: RelationshipType
    is_deterministic: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
