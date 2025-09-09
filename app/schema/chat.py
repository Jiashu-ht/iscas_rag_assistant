from fastapi import UploadFile, Form
from pydantic import BaseModel, Field
from typing import Dict, Optional, List
import json

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
    talk_id: str
    query: str
    # files: List[UploadFile] = Field(default_factory=list)
    file_ids: list[str] = Field(default_factory=list)
    history: list = Field(default_factory=list)

# 2. 定义依赖函数：从表单数据构造模型
async def get_chat_summary_request(
    talk_id: str = Form(...),
    query: str = Form(...),
    file_ids: list[str] = Form(default_factory=list),
    history: str = Form("[]")  # 前端传JSON字符串，默认空列表
) -> ChatSummaryRequest:
    # 解析history（前端传JSON字符串，需转为List）
    try:
        history_list = json.loads(history) if history else []
    except json.JSONDecodeError:
        history_list = []
    return ChatSummaryRequest(
        talk_id=talk_id,
        query=query,
        file_ids=file_ids,
        history=history_list
    )