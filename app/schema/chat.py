from pydantic import BaseModel, Field
from typing import Dict, Optional, List

class SingleFileChatRequest(BaseModel):
    file_id: str
    query: str
    history: List = Field(default_factory=list)
    top_k: Optional[int] = 5

class ChatRequest(BaseModel):
    query: str
    history: List = Field(default_factory=list)
    top_k: Optional[int] = 5

class ChatSummaryRequest(BaseModel):
    query: str
    