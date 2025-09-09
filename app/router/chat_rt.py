from fastapi import APIRouter, UploadFile, Form, Depends, File
from ragflow_sdk import Chunk
import time

from schema.chat import SingleFileChatRequest, ChatRequest, ChatSummaryRequest, get_chat_summary_request
from service.llm import construct_prompt, query_vllm, generate_rag_query
from service.ragflow import get_ragflow_client_and_dataset
from service.sqlite import save_mapping, get_ragflow_id_by_client_id, get_other_by_ragflow_id, save_talk_dataset_mapping, save_talk_document_mapping, get_dataset_id_by_talk_id, get_document_ids_by_talk_id


router = APIRouter()

@router.post("/upload_file")
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
    new_query = request.query
    if request.history:
        new_query_prompt = generate_rag_query(request.history, request.query)
        new_query = query_vllm(user_prompt=new_query_prompt)
    
    print(f"new query:-------------------\n{new_query}")
    contexts = client.retrieve(question=new_query, dataset_ids=[dataset.id], document_ids=[ragflow_id])

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

    new_query = request.query
    if request.history:
        new_query_prompt = generate_rag_query(request.history, request.query)
        new_query = query_vllm(user_prompt=new_query_prompt)

    # 检索相关块
    contexts = client.retrieve(question=new_query, dataset_ids=[dataset.id])

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
    # print("---")
    # print( type(contexts) )
    # for i in contexts:
    #     print(i)
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

@router.post("/chat_summary")
async def chat_summary(
    request: ChatSummaryRequest = Depends(get_chat_summary_request), 
    files: list[UploadFile] = File(default_factory=list)
):
    client, _ = get_ragflow_client_and_dataset()  # 获取基础客户端
    
    # 1. 检查会话是否存在
    dataset_id = get_dataset_id_by_talk_id(request.talk_id)
    is_new_talk = not dataset_id
    
    # 2. 处理新建会话
    if is_new_talk:
        # 创建新的dataset
        dataset_name = f"{request.talk_id}_talk"
        dataset = client.create_dataset(name=dataset_name)
        dataset_id = dataset.id
        save_talk_dataset_mapping(request.talk_id, dataset_id)
    else:
        # 获取已有dataset
        datasets = client.list_datasets(name=f"{request.talk_id}_talk")
        dataset = datasets[0]
    
    # 3. 处理文件上传（新会话或有新文件的旧会话）   
    doc_id_and_name = []  # ragflow_id
    if files:
        for file in files:
            # 保存文档到本地
            file_name = f"{file.filename}"
            file_path = f"./dataset/docs/{file_name}"
            with open(file_path, "wb") as f:
                f.write(await file.read())
            
            # 上传到ragflow数据库
            documents =[{"display_name": file_name, "blob":open(file_path, "rb").read()}]
            docs = dataset.upload_documents(documents)
            
            # 获取ragflow文档id
            documents = dataset.list_documents(keywords=file_name)
            for doc in documents:
                # 保存会话与文档的映射
                save_talk_document_mapping(request.talk_id, doc.id)
                doc_id_and_name.append((doc.id, file.filename))
            
            # 启动异步解析
            dataset.async_parse_documents([doc.id for doc in documents])
    else:
        for id in get_document_ids_by_talk_id(talk_id=request.talk_id):
            for d in dataset.list_documents(id=id):
                doc_id_and_name.append((id, d.name))


    # id数量应该是和文件数量相等的
    if request.file_ids:
        for i, client_id in enumerate(request.file_ids):
            save_mapping(client_id=client_id, ragflow_id=doc_id_and_name[i][0], file_name=doc_id_and_name[i][1])

    
    # 4. 生成摘要
    # 获取所有文档内容
    all_documents_content = []
    references = []
    
    for doc_id_name in doc_id_and_name:
        # 获取文档所有文本块
        the_docs = dataset.list_documents(keywords=doc_id_name[1])
        # print(f"doc_name = {doc_id_name[1]}")
        file_content = []
        for chunk in the_docs[0].list_chunks():
            # print(f"chunk: \n{chunk.content}")
            # 拼接成全文
            file_content.append(chunk.content)
        file_content = "\n".join(file_content)
        all_documents_content.append(f"文档名称：{doc_id_name[1]}\n 内容：{file_content}")
    
    # 构造提示词
    documents_str = "\n\n---\n\n".join([f"文档 {i+1}, {content}" for i, content in enumerate(all_documents_content)])

    summary_prompt = f"""
# 任务
根据用户查询和提供的文档内容，生成相应的摘要信息。

# 文档内容
{documents_str}

# 用户查询
{request.query}

# 查询分类
1. 如果查询要求提取关键词，返回5-10个最相关的关键词
2. 如果查询要求总结，提供简洁明了的摘要
3. 如果查询要求梳理知识要点，使用分点列出关键信息

# 回答要求
1. 按查询分类结果回答问题，没有要求就不要回答
2. 基于提供的所有文档内容进行回答
3. 确保回答准确反映文档的核心内容
3. 如果相关文档不存在，则回答文档不存在或者正在解析中。



请根据用户查询类型，生成严格符合要求的回答。
"""

    # 调用LLM生成结果
    answer = query_vllm(user_prompt=summary_prompt, history=request.history)
    
    # 6. 返回结果
    return {
        "status": "success",
        "answer": answer,
        "reference": references,
        "message": ""
    }