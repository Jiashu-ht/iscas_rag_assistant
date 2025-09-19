import requests
import json
import time
from typing import Dict, List

class SingleFileChatTester:
    def __init__(self, base_url: str = "http://localhost:10081"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "SingleFileChatTester/1.0"
        })
    
    def test_single_chat(self, file_id: str, query: str, history: list = None, top_k: int = 5):
        """测试单次聊天"""
        payload = {
            "file_id": file_id,
            "query": query,
            "history": history or [],
            "top_k": top_k
        }
        print(payload)
        
        try:
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/single_file_chat",
                json=payload,
                timeout=30
            )
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 请求成功 (耗时: {end_time - start_time:.2f}s)")
                print(f"   状态: {data['status']}")
                print(f"   回答: {data['answer']}..." if data.get('answer') else "   无回答")
                print(f"   消息: {data.get('message', '无')}")
                return data
            else:
                print(f"❌ 请求失败: HTTP {response.status_code}")
                print(f"   错误信息: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求错误: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
            return None
    
    def run_comprehensive_test(self):
        """运行全面的测试用例"""
        test_cases = [
            {
                "name": "正常聊天测试",
                "file_id": "valid_file_001",  # 替换为有效文件ID
                "query": "请总结这个文档的主要内容",
                "top_k": 3
            },
            {
                "name": "带历史记录的聊天",
                "file_id": "valid_file_001",
                "query": "基于之前的讨论，能提供更多细节吗？",
                "history": {
                    "user": "这个文档的主题是什么？",
                    "assistant": "文档主要讨论了机器学习的基本原理。"
                },
                "top_k": 5
            },
            {
                "name": "测试不同top_k值",
                "file_id": "valid_file_001",
                "query": "文档中有哪些关键技术？",
                "top_k": 1  # 测试较小的top_k
            },
            {
                "name": "测试空文件ID",
                "file_id": "",
                "query": "这是一个测试问题",
                "top_k": 5
            }
        ]
        
        print("🚀 开始单文件聊天接口测试")
        print("=" * 60)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 测试用例 {i}: {test_case['name']}")
            print(f"   File ID: {test_case['file_id']}")
            print(f"   Query: {test_case['query']}")
            print(f"   Top K: {test_case.get('top_k', 5)}")
            
            self.test_single_chat(
                file_id=test_case["file_id"],
                query=test_case["query"],
                history=test_case.get("history"),
                top_k=test_case.get("top_k", 5)
            )
            
            print("-" * 40)

def main():
    # 创建测试器实例
    tester = SingleFileChatTester("http://localhost:10081")  # 修改为您的实际地址
    
    # 运行单个测试
    print("单个测试示例:")
#     history = [
#         {"role": "user", "content": "车用PCB发展态势如何"},
#         {"role": "assistant", "content": """为了回答您的问题，我需要了解具体的车用PCB行业发展状况和趋势。但是，根据当前的信息，我可以为您提供一些一般性的看法。

# 从参考上下文中可以看出，车用PCB领域的市场需求正在增加，特别是在新能源+数通领域有明显的增长潜力。然而，由于下游渠道在一定程度上受到了库存调整的影响，导致了公司的收入环比上升。不过，这些数据只是部分反映市场情况，具体的发展前景还需要进一步观察和分析。

# 综上所述，车用PCB行业的发展态势仍然存在不确定性，需要密切关注行业动态和发展趋势，以制定更有效的策略。"""}
#     ]
    result = tester.test_single_chat(
        file_id="4154",  # 替换为实际文件ID
        query="政治",
        # top_k=3,
        # history=history
    )
    
    # 或者运行全面测试
    # tester.run_comprehensive_test()

if __name__ == "__main__":
    main()