"""
Pydantic schemas for ThreatDesk data models, plans, validation, execution, and explanation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PlanResponse(BaseModel):
    sql: str = Field(..., description="Generated Snowflake SQL query")
    reasoning: str = Field(..., description="Explanation of how the query addresses the user's question")

class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether the SQL query passed validation")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    cleaned_sql: Optional[str] = Field(None, description="Validated and formatted SQL query")

class ExecutionResult(BaseModel):
    success: bool = Field(..., description="Whether execution succeeded")
    columns: List[str] = Field(default_factory=list, description="Column names")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Result rows as dictionaries")
    row_count: int = Field(0, description="Number of rows returned")
    error: Optional[str] = Field(None, description="Execution error message if failed")
    sfqid: Optional[str] = Field(None, description="Snowflake Query ID")
    execution_time: Optional[float] = Field(None, description="Query execution time in seconds")

class ExplainerResponse(BaseModel):
    explanation: str = Field(..., description="Natural language explanation grounded in execution results")
