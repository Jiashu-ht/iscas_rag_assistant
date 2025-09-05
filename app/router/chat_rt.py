from fastapi import APIRouter, UploadFile, Form
from ragflow_sdk import Chunk
import time

from schema.chat import SingleFileChatRequest, ChatRequest
from service.llm import construct_prompt, query_vllm
from service.ragflow import get_ragflow_client_and_dataset
from service.sqlite import save_mapping, get_ragflow_id_by_client_id, get_other_by_ragflow_id

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile, file_id: str = Form(...)):
    _, dataset = get_ragflow_client_and_dataset()

    # 检查是否已经上传过, 不为空说明已上传
    ragflow_id = get_ragflow_id_by_client_id(file_id)
    if ragflow_id:
        return {
            "status": "failure",
            "message": "Please do not upload repeatedly",
        }

    # 保存文档到本地
    file_name = f"{file_id}_{file.filename}"
    file_path = f"./dataset/docs/{file_name}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # 上传到ragflow数据库
    documents =[{"display_name": file_name, "blob":open(file_path, "rb").read()}]
    docs = dataset.upload_documents(documents)

    # 获取ragflow数据库中该文档的id
    documents = dataset.list_documents(keywords=file_name)
    ids = []
    for document in documents:
        ids.append(document.id)

    # 启动异步解析文档，解析需要一定时间，具体看文档大小和复杂度
    # 文档解析，文本分块，向量嵌入和存储
    dataset.async_parse_documents(ids)

    # 保存 file_id 和 ragflow_id 的映射，方便后续操作
    save_mapping(file_id, ids[0], file.filename)
    return {
        "status": "success",
        "message": "File upload successfully. It takes some time to complete the parsing task. "
                  + "Please wait for one minute after the initial upload before starting the conversation",
    }


@router.post("/single_file_chat")
async def single_file_chat(request: SingleFileChatRequest):
    client, dataset = get_ragflow_client_and_dataset()

    # 检索相关块
    ragflow_id = get_ragflow_id_by_client_id(request.file_id)
    contexts = client.retrieve(question=request.query, dataset_ids=[dataset.id], document_ids=[ragflow_id])

    # 没有解析完成
    if not contexts:
        return {
            "status": "failure",
            "answer": "",
            "message": "The document is currently being parsed, please have a conversation later."
        }

    # 保留前 top_k 个
    if len(contexts) > request.top_k:
        contexts = contexts[:request.top_k]

    # 调用大模型生成结果，单文件对话不需要返回文档id
    # print(contexts)
    prompt = construct_prompt(request.query, contexts)
    answer = query_vllm(user_prompt=prompt, history=request.history)

    return {
        "status": "success",
        "answer": answer,
        "message": ""
    }

@router.post("/chat")
async def chat(request: ChatRequest):
    client, dataset = get_ragflow_client_and_dataset()

    # 检索相关块
    contexts = client.retrieve(question=request.query, dataset_ids=[dataset.id])

    # 没有解析完成
    if not contexts:
        return {
            "status": "failure",
            "answer": "",
            "message": "The document is currently being parsed, please have a conversation later."
        }

    # 保留前 top_k 个
    if len(contexts) > request.top_k:
        contexts = contexts[:request.top_k]

    # 调用大模型生成结果，多文件对话需要返回文档id，文本块
    prompt = construct_prompt(request.query, contexts)
    answer = query_vllm(user_prompt=prompt, history=request.history)

    # 附带参考数据返回
    reference = []
    print("---")
    print( type(contexts) )
    for i in contexts:
        print(i)
    if isinstance(contexts, list):
        for ctx in contexts:
            file_id, file_name = get_other_by_ragflow_id(ctx.document_id)
            reference.append({
                "file_id": file_id,
                "file_name": file_name,
                "chunk": ctx.content,
                "similarity": ctx.similarity
            })
    
    return {
        "status": "success",
        "answer": answer,
        "reference": reference,
        "message": ""
    }