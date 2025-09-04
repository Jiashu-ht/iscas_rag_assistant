import json
import requests

from service.sqlite import get_other_by_ragflow_id

def query_vllm(system_prompt="", user_prompt="", history=None, model="Qwen2.5-7B-Instruct"):
    headers = {
        "Content-Type": "application/json"
    }
    url = "http://localhost:8002/v1/chat/completions"
    
    # 构造聊天历史
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    if history:
        messages.extend(history)  # 历史必须是 [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}] 这样的格式
    
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 512,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"调用失败：{e}")
        return ""

# def query_vllm(prompt):
#     headers = {
#             "Content-Type": "application/json"
#         }
#     url = f"http://localhost:8002/v1/chat/completions"
#     payload = { 
#         "model": "Qwen2.5-7B-Instruct",
#         "messages": [
#             {"role": "user", "content": prompt}
#         ],
#         "temperature": 0.8,
#         "max_tokens": 512,
#     }
#     try:
#         response = requests.post(url, headers=headers, json=payload, timeout=60)
#         response.raise_for_status()
#         result = response.json()
#         return result['choices'][0]['message']['content'].strip()
#     except Exception as e:
#         print(f"调用失败：{e}")
#         return ""
    

# # 单轮调用：
# result = query_vllm(
#     system_prompt="你是一个段子手",
#     user_prompt="请来一个搞笑段子"
# )
# print(result)

# # 多轮对话调用：
# history = [
#     {"role": "user", "content": "请你分析下面的句子"},
#     {"role": "assistant", "content": "当然，请提供句子"}
# ]
# result = query_vllm(
#     system_prompt="你是一个逻辑清晰的标注专家。",
#     user_prompt="‘隐私权是基本人权，任何侵犯都应受到约束’ 是主要论点吗？",
#     history=history
# )
# print(result)

def construct_prompt(question, contexts):
    # 将检索到的上下文组合成字符串
    context_str = []
    for i, ctx in enumerate(contexts):
        file_id, file_name = get_other_by_ragflow_id(ctx['document_id'])
        context_str.append(f"[上下文片段 {i+1}]:\n{ctx['content']}\n来源: 文档编号-{file_id}, 文档名称-{file_name}")
    context_str = "\n\n".join(context_str)
    
    prompt = f"""
# 角色与任务
你是一个专业、准确且可靠的AI助手。你的任务是基于提供的参考上下文信息，回答用户的问题。

# 参考上下文
以下是相关的参考信息：
{context_str}

# 用户问题
{question}

# 回答要求
1. 仅使用上述参考上下文中的信息来回答问题，不要依赖外部知识
2. 如果参考上下文中的信息不足以回答这个问题，请明确说明"根据提供的信息，无法完全回答此问题"
3. 确保回答准确、客观，避免主观臆断或猜测
4. 保持回答简洁明了，但内容完整
5. 如果参考上下文中有相互矛盾的信息，请指出这种矛盾，并尽可能提供最合理的解释
6. 对于涉及数字、日期或具体事实的信息，请确保与参考上下文一致

# 安全与责任限制
1. 不提供医疗、法律或金融方面的专业建议，只能提供参考信息
2. 不生成任何有害、歧视性或不适当的内容
3. 不分享个人观点或政治立场
4. 如果问题涉及敏感话题，请保持中立并基于事实回答

# 输出格式
- 首先直接回答问题
- 然后简要解释答案的依据（引用相关上下文片段）
- 最后可以补充相关的额外信息（如果参考上下文中有）

请根据以上要求生成回答。
"""
    
    return prompt