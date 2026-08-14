from datetime import datetime

from pydantic import BaseModel


class TaskDependencyCreate(BaseModel):
    depends_on_task_id: int


class TaskDependencyOut(BaseModel):
    id: int
    task_id: int
    depends_on_task_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
