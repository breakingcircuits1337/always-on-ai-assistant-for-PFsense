from pydantic import BaseModel, Field
from typing import Optional


class MockDataType(BaseModel):
    id: str
    name: str


class Task(BaseModel):
    task_name: str
    priority: int
    delay: int
    task_id: Optional[str] = Field(default=None)
