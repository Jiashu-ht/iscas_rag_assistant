from fastapi import APIRouter, UploadFile, Form, Depends, File
from fastapi.responses import JSONResponse
from ragflow_sdk import Chunk
import time, threading, requests, shutil
from pathlib import Path

from schema.chat import SingleFileChatRequest, ChatRequest, ChatSummaryRequest, get_chat_summary_request
from service.llm import construct_prompt, query_vllm, generate_rag_query
from service.ragflow import get_ragflow_client_and_dataset
from service.sqlite import save_mapping, get_ragflow_id_by_client_id, get_other_by_ragflow_id, save_talk_dataset_mapping, save_talk_document_mapping, get_dataset_id_by_talk_id, get_document_ids_by_talk_id, save_talk_doc_mapping, get_docs_by_talk_id
from service.doc_parse import parse_documents


router = APIRouter()

# @router.post("/upload_file")
# async def upload_file(file: UploadFile, file_id: str = Form(...)):
#     _, dataset = get_ragflow_client_and_dataset()

#     # 检查是否已经上传过, 不为空说明已上传
#     ragflow_id = get_ragflow_id_by_client_id(file_id)
#     if ragflow_id:
#         return {
#             "status": "failure",
#             "message": "Please do not upload repeatedly",
#         }

#     # 保存文档到本地
#     file_name = f"{file_id}_{file.filename}"
#     file_path = f"./dataset/docs/{file_name}"
#     with open(file_path, "wb") as f:
#         f.write(await file.read())

#     # 上传到ragflow数据库
#     documents =[{"display_name": file_name, "blob":open(file_path, "rb").read()}]
#     docs = dataset.upload_documents(documents)

#     # 获取ragflow数据库中该文档的id
#     documents = dataset.list_documents(keywords=file_name)
#     ids = []
#     for document in documents:
#         ids.append(document.id)

#     # 启动异步解析文档，解析需要一定时间，具体看文档大小和复杂度
#     # 文档解析，文本分块，向量嵌入和存储
#     dataset.async_parse_documents(ids)

#     # 保存 file_id 和 ragflow_id 的映射，方便后续操作
#     save_mapping(file_id, ids[0], file.filename)
#     return {
#         "status": "success",
#         "message": "File upload successfully. It takes some time to complete the parsing task. "
#                   + "Please wait for one minute after the initial upload before starting the conversation",
#     }

# # 定义后台处理文件的函数（同步函数，不含await）
# def process_file_in_background(file_content, file_id, file_name):
#     try:
#         _, dataset = get_ragflow_client_and_dataset()
        
#         # 保存文档到本地
#         save_path = f"./dataset/docs/{file_id}_{file_name}"
#         with open(save_path, "wb") as f:
#             f.write(file_content)  # 使用已读取的文件内容
        
#         # 上传到ragflow数据库
#         documents = [{"display_name": f"{file_id}_{file_name}", "blob": file_content}]
#         docs = dataset.upload_documents(documents)
        
#         # 获取ragflow数据库中该文档的id
#         documents = dataset.list_documents(keywords=f"{file_id}_{file_name}")
#         if documents:
#             ragflow_id = documents[0].id
            
#             # 启动异步解析文档
#             dataset.async_parse_documents([ragflow_id])
            
#             # 保存映射关系
#             save_mapping(file_id, ragflow_id, file_name)
#         else:
#             # 处理未找到文档的情况（可添加日志）
#             pass
            
#     except Exception as e:
#         # 记录错误日志（建议使用logging模块）
#         print(f"文件处理失败: {str(e)}")

# @router.post("/upload_file")
# async def upload_file(file: UploadFile, file_id: str = Form(...)):
#     # 检查是否已经上传过
#     ragflow_id = get_ragflow_id_by_client_id(file_id)
#     if ragflow_id:
#         return JSONResponse({
#             "status": "failure",
#             "message": "Please do not upload repeatedly",
#         })
    
#     # 先读取文件内容到内存（避免线程中文件对象被关闭）
#     file_content = await file.read()
#     file_name = file.filename
    
#     # 创建并启动后台线程处理文件
#     thread = threading.Thread(
#         target=process_file_in_background,
#         args=(file_content, file_id, file_name)
#     )
#     thread.daemon = True  # 设为守护线程，主程序退出时自动结束
#     thread.start()
    
#     # 立即返回响应，不等待处理完成
#     return JSONResponse({
#         "status": "success",
#         "message": "File upload request received. It is being processed in the background. "
#                   + "Please wait for a while before starting the conversation.",
#     })


@router.post("/single_file_chat")
async def single_file_chat(request: SingleFileChatRequest):
    client, dataset = get_ragflow_client_and_dataset()
 
    # 检索相关块
    ragflow_id = get_ragflow_id_by_client_id(request.file_id)
    new_query = request.query
    print(request)
    processed_lis = []
    # lis = eval(request.history)
    if request.history:
        import json
        lis = json.loads( request.history )
        print( type(lis) )
        for i in lis:
            print(i , type(i))
            processed_lis.append( {"role": i["role"], "content": i["content"]} )
        new_query_prompt = generate_rag_query(lis, request.query)
        new_query = query_vllm(user_prompt=new_query_prompt , history = processed_lis)
    
    # print(f"new query:-------------------\n{new_query}")
    contexts = client.retrieve(question=new_query, dataset_ids=[dataset.id], document_ids=[ragflow_id])

    # 没有解析完成
    # if not contexts:
    #     return {
    #         "status": "failure",
    #         "answer": "",
    #         "message": "The document is currently being parsed, please have a conversation later."
    #     }

    # 保留前 top_k 个
    if len(contexts) > request.top_k:
        contexts = contexts[:request.top_k]

    # 调用大模型生成结果，单文件对话不需要返回文档id
    # print(contexts)
    prompt = construct_prompt(request.query, contexts)
    answer = query_vllm(user_prompt=prompt, history=processed_lis)
    print("ans \n\n" , answer , "\n\n")

    return {
        "status": "success",
        "answer": answer,
        "message": ""
    }

@router.post("/chat")
async def chat(request: ChatRequest):
    client, dataset = get_ragflow_client_and_dataset()

    processed_lis = []
    new_query = request.query
    if request.history:
        import json
        lis = json.loads( request.history )
        print( type(lis) )
        
        for i in lis:
            print(i , type(i))
            processed_lis.append( {"role": i["role"], "content": i["content"]} )
        new_query_prompt = generate_rag_query(lis, request.query)
        new_query = query_vllm(user_prompt=new_query_prompt, history=processed_lis)

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
    answer = query_vllm(user_prompt=prompt, history=processed_lis)

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
async def chat_summary(request: ChatSummaryRequest = Depends(get_chat_summary_request), files: list[UploadFile] = File(default_factory=list)):
    '''
    使用ragflow解析文档，处理流程略微复杂，可以考虑接口 /chat_summary_2
    文件只有首次上传时需要提供 files和file_ids，且数量一致
    '''
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

# @router.post("/chat_summary_2")
# async def chat_summary(
#     request: ChatSummaryRequest = Depends(get_chat_summary_request), 
#     files: list[UploadFile] = File(default_factory=list)
# ):
#     '''
#     直接使用文档解析工具解析得到文本，速度快很多
#     文件只有首次上传时需要提供 files和file_ids，且数量一致
#     '''
#     doc_id_and_name = []
#     if files:
#         ids = [id for id in request.file_ids]
#         for file, id in zip(files, ids):
#             # 保存文档到本地
#             file_name = f"{id}_{file.filename}"
#             print(file_name)
#             file_path = f"./dataset/docs/{file_name}"
#             with open(file_path, "wb") as f:
#                 f.write(await file.read())
            
#             doc_id_and_name.append((id, file.filename))
#             save_talk_doc_mapping(request.talk_id, id, file.filename)
            
#     else:
#         for id, name in get_docs_by_talk_id(request.talk_id):
#             doc_id_and_name.append((id, name))


    
#     # 4. 生成摘要
#     # 获取所有文档内容

#     all_doc_names = []
#     references = []
    
#     for id, name in doc_id_and_name:
#         all_doc_names.append(f"{id}_{file.filename}")
    
#     all_documents_content = parse_documents(all_doc_names, "./dataset/docs/")
    
#     summary_prompt = f"""
# # 任务
# 根据用户查询和提供的文档内容，生成相应的摘要信息。

# # 文档内容
# {all_documents_content}

# # 用户查询
# {request.query}

# # 查询分类
# 1. 如果查询要求提取关键词，返回5-10个最相关的关键词
# 2. 如果查询要求总结，提供简洁明了的摘要
# 3. 如果查询要求梳理知识要点，使用分点列出关键信息

# # 回答要求
# 1. 按查询分类结果回答问题，没有要求就不要回答
# 2. 基于提供的所有文档内容进行回答
# 3. 确保回答准确反映文档的核心内容
# 3. 如果相关文档不存在，则回答文档不存在或者正在解析中。



# 请根据用户查询类型，生成严格符合要求的回答。
# """

#     # 调用LLM生成结果
#     answer = query_vllm(user_prompt=summary_prompt, history=request.history)
    
#     # 6. 返回结果
#     return {
#         "status": "success",
#         "answer": answer, 
#         "reference": references,
#         "message": ""
#     }

def download_file_from_server(save_path: Path , download_path:str):
    file_server_url = "http://192.168.100.72:8915/bigdata/resume/downloadResume"  # 文件服务器接口
    params = {"path": download_path}  # 文件ID通过参数传递
    resp = requests.get(file_server_url, params=params, stream=True)
    if resp.status_code != 200:
        raise Exception(f"文件服务器返回状态码: {resp.status_code}")

    with save_path.open("wb") as f:
        shutil.copyfileobj(resp.raw, f)

# 定义后台处理文件的函数（同步函数，不含await）
def process_file_in_background(file_id: str, file_name: str, path: str):
    try:
        _, dataset = get_ragflow_client_and_dataset()
        
        # 创建保存目录
        save_dir = Path("./dataset/docs")
        save_dir.mkdir(exist_ok=True)
        save_path = save_dir / f"{file_id}_{file_name}"


        # download_file_from_server(save_path, path)
        # 从文件服务器下载文件
        file_server_url = "http://192.168.100.72:8915/bigdata/resume/downloadResume"
        params = {"path": path}
        resp = requests.get(file_server_url, params=params, stream=True)
        
        if resp.status_code != 200:
            raise Exception(f"文件下载失败，状态码: {resp.status_code}")
        

        # 保存文件到本地
        with save_path.open("wb") as f:
            shutil.copyfileobj(resp.raw, f)

        # 上传到ragflow数据库
        with save_path.open("rb") as f:
            documents = [{"display_name": f"{file_id}_{file_name}", "blob": f.read()}]
        docs = dataset.upload_documents(documents)
        
        # 获取ragflow数据库中该文档的id
        documents = dataset.list_documents(keywords=f"{file_id}_{file_name}")
        if documents:
            ragflow_id = documents[0].id
            
            # 启动异步解析文档
            dataset.async_parse_documents([ragflow_id])
            
            # 保存映射关系
            save_mapping(file_id, ragflow_id, file_name)
        else:
            raise Exception("上传到ragflow后未找到文档")
            
    except Exception as e:
        # 记录错误日志（建议使用logging模块）
        print(f"文件处理失败: {str(e)}")
        # 可添加文件清理逻辑
        if save_path.exists():
            save_path.unlink()

@router.post("/upload_file")
def upload_file(file_id: str = Form(...), path: str = Form(...)):
    # 检查是否已经上传过
    ragflow_id = get_ragflow_id_by_client_id(file_id)
    if ragflow_id:
        return JSONResponse({
            "status": "failure",
            "message": "Please do not upload repeatedly",
        })
    
    # 从路径中提取文件名
    if "//" in path:
        file_name = path.split("//")[-1]
    else:
        file_name = Path(path).name
    # 创建并启动后台线程处理文件
    thread = threading.Thread(
        target=process_file_in_background,
        args=(file_id, file_name, path)
    )
    thread.daemon = True  # 设为守护线程，主程序退出时自动结束
    thread.start()
    
    # 立即返回响应，不等待处理完成
    return JSONResponse({
        "status": "success",
        "message": "File upload request received. It is being processed in the background. "
                  + "Please wait for a while before starting the conversation.",
    })


# = Depends(get_chat_summary_request)
@router.post("/chat_summary_2")
async def chat_summary(request: ChatSummaryRequest):
    '''
    直接使用文档解析工具解析得到文本，速度快很多
    文件只有首次上传时需要提供file_paths和file_ids，且数量一致
    '''


    doc_id_and_name = []
    if request.file_ids and request.file_paths:
        import json
        file_ids = json.loads(request.file_ids)
        file_paths = json.loads(request.file_paths)

        # 检查file_paths和file_ids数量是否一致
        if len(file_paths) != len(file_ids):
            return {
                "status": "failure",
                "message": "file_paths and file_ids must have the same length"
            }
        
        # 创建保存目录（确保目录存在）
        save_dir = Path("./dataset/docs")
        save_dir.mkdir(exist_ok=True)
        
        # 文件服务器地址（可考虑移至环境变量）
        file_server_url = "http://192.168.100.72:8915/bigdata/resume/downloadResume"
        
        for path, file_id in zip(file_paths, file_ids):
            try:
                # 从路径中提取文件名
                if "//" in path:
                    file_name = path.split("//")[-1]
                else:
                    file_name = Path(path).name
                
                # 本地保存路径
                save_path = save_dir / f"{file_id}_{file_name}"
                
                # 从文件服务器下载文件
                resp = requests.get(
                    file_server_url,
                    params={"path": path},
                    stream=True,
                    timeout=30  # 添加超时控制
                )
                resp.raise_for_status()  # 抛出HTTP错误状态码
                
                # 保存文件到本地
                with open(save_path, "wb") as f:
                    shutil.copyfileobj(resp.raw, f)
                
                # 记录文档ID和名称映射，建立talk与文档关联
                doc_id_and_name.append((file_id, file_name))
                save_talk_doc_mapping(request.talk_id, file_id, file_name)
                
            except Exception as e:
                # 处理单文件下载失败（可根据需求选择继续或中断）
                print(f"文件处理失败（path: {path}, id: {file_id}）: {str(e)}")
                return {
                    "status": "failure",
                    "message": f"Failed to process file {file_name}: {str(e)}"
                }
    else:
        # 无新文件时，从数据库获取已有关联文档
        for id, name in get_docs_by_talk_id(request.talk_id):
            doc_id_and_name.append((id, name))
    
    # 生成摘要（保持原有逻辑）
    all_doc_names = []
    references = []
    
    for id, name in doc_id_and_name:
        all_doc_names.append(f"{id}_{name}")  # 使用已提取的name而非file.filename
    
    all_documents_content = parse_documents(all_doc_names, "./dataset/docs/")
    
    summary_prompt = f"""
# 任务
根据用户查询和提供的文档内容，按查询分类完成任务。

# 文档内容
{all_documents_content}

# 用户查询
{request.query}

# 查询分类
1. 如果查询要求提取关键词，返回5-10个最相关的关键词，否则不提取关键词。
2. 如果查询要求总结，提供简洁明了的摘要，否则不进行总结
3. 如果查询要求梳理知识要点，使用分点列出关键信息，否则不列出关键信息
4. 如果是其他查询，根据文档内容回答。

# 回答要求
1. 按查询分类结果回答问题，没有要求就不要回答
2. 基于提供的所有文档内容进行回答
3. 确保回答准确反映文档的核心内容
3. 如果相关文档不存在，则回答文档不存在或者正在解析中。

请根据用户查询类型，生成严格符合要求的回答。

回答如下：
"""
    processed_lis = []
    if request.history:
        import json
        lis = json.loads( request.history )
        print( type(lis) )
        
        for i in lis:
            print(i , type(i))
            processed_lis.append( {"role": i["role"], "content": i["content"]} )
    # 调用LLM生成结果
    answer = query_vllm(user_prompt=summary_prompt, history=processed_lis)

    # print("ans" + answer)
    
    # 返回结果
    return {
        "status": "success",
        "answer": answer,
        "reference": references,
        "message": ""
    }

# = Depends(get_chat_summary_request)
@router.post("/chat_keyword")
async def chat_keyword(request: ChatSummaryRequest):
    '''
    直接使用文档解析工具解析得到文本，速度快很多
    文件只有首次上传时需要提供file_paths和file_ids，且数量一致
    '''


    doc_id_and_name = []
    if request.file_ids and request.file_paths:
        import json
        file_ids = json.loads(request.file_ids)
        file_paths = json.loads(request.file_paths)

        # 检查file_paths和file_ids数量是否一致
        if len(file_paths) != len(file_ids):
            return {
                "status": "failure",
                "message": "file_paths and file_ids must have the same length"
            }
        
        # 创建保存目录（确保目录存在）
        save_dir = Path("./dataset/docs")
        save_dir.mkdir(exist_ok=True)
        
        # 文件服务器地址（可考虑移至环境变量）
        file_server_url = "http://192.168.100.72:8915/bigdata/resume/downloadResume"
        
        for path, file_id in zip(file_paths, file_ids):
            try:
                # 从路径中提取文件名
                if "//" in path:
                    file_name = path.split("//")[-1]
                else:
                    file_name = Path(path).name
                
                # 本地保存路径
                save_path = save_dir / f"{file_id}_{file_name}"
                
                # 从文件服务器下载文件
                resp = requests.get(
                    file_server_url,
                    params={"path": path},
                    stream=True,
                    timeout=30  # 添加超时控制
                )
                resp.raise_for_status()  # 抛出HTTP错误状态码
                
                # 保存文件到本地
                with open(save_path, "wb") as f:
                    shutil.copyfileobj(resp.raw, f)
                
                # 记录文档ID和名称映射，建立talk与文档关联
                doc_id_and_name.append((file_id, file_name))
                save_talk_doc_mapping(request.talk_id, file_id, file_name)
                
            except Exception as e:
                # 处理单文件下载失败（可根据需求选择继续或中断）
                print(f"文件处理失败（path: {path}, id: {file_id}）: {str(e)}")
                return {
                    "status": "failure",
                    "message": f"Failed to process file {file_name}: {str(e)}"
                }
    else:
        # 无新文件时，从数据库获取已有关联文档
        for id, name in get_docs_by_talk_id(request.talk_id):
            doc_id_and_name.append((id, name))
    
    # 生成摘要（保持原有逻辑）
    all_doc_names = []
    references = []
    
    for id, name in doc_id_and_name:
        all_doc_names.append(f"{id}_{name}")  # 使用已提取的name而非file.filename
    
    all_documents_content = parse_documents(all_doc_names, "./dataset/docs/")
    
    keyword_prompt = f"""
【任务】
请基于以下目标【文档内容】，严格按照以下规定提取关键词

【文档内容】
{all_documents_content}

【用户查询】
{request.query}

【回答要求】
1. 关键词需要精准反映文本核心主题、核心概念或核心对象，避免无关紧要或者次要信息。
2. 优先选择文本中明确出现的名词或名词性短语，若核心概念中无直接名词，可提炼简洁性的概括性短语。
3. 关键词控制在10-20个，每个关键词除非经常整体出现，如“中国特色社会主义思想”，否则尽量保持简短。
4. 若文本包含多个核心维度，需要覆盖各个主要维度，不要遗漏关键信息。越重要的关键词越靠前。
5. 回答格式：直接回答出各个关键词，用“，”隔开。不用包含任何其他多余信息。例如：“人工智能，深度学习，机器学习，chatgpt,科技，工业革命，aigc，openai,meta”

请根据用户查询，生成严格符合要求的回答。

文章关键词如下：
"""
    processed_lis = []
    if request.history:
        import json
        lis = json.loads( request.history )
        print( type(lis) )
        
        for i in lis:
            print(i , type(i))
            processed_lis.append( {"role": i["role"], "content": i["content"]} )
    # 调用LLM生成结果
    answer = query_vllm(user_prompt=keyword_prompt, history=processed_lis)


    print("KEYWORD：" + answer)
    
    # 返回结果
    return {
        "status": "success",
        "answer": answer,
        "reference": references,
        "message": ""
    }