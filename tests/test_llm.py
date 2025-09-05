import requests

def query_vllm(system_prompt="", user_prompt="", history=None, model="Qwen2.5-7B-Instruct"):
    headers = {
        "Content-Type": "application/json"
    }
    url = "http://172.17.0.1:10000/v1/chat/completions"
    
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

print(query_vllm(user_prompt="来一个冷笑话"))