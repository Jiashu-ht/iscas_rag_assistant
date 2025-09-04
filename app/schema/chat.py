from pydantic import BaseModel, Field
from typing import Dict, Optional

class SingleFileChatRequest(BaseModel):
    file_id: str
    query: str
    history: Dict[str, str] = Field(default_factory=dict)
    top_k: Optional[int] = 5

class ChatRequest(BaseModel):
    query: str
    history: Dict[str, str] = Field(default_factory=dict)
    top_k: Optional[int] = 5