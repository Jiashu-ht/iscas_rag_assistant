import requests
import json
import time
from typing import Dict, List, Optional
from pathlib import Path

class ChatSummaryTester:
    def __init__(self, base_url: str = "http://localhost:10081"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ChatSummaryTester/1.0"
        })
        # 创建临时测试文件目录
        self.test_files_dir = Path("tests/summary_test_files")
        self.test_files_dir.mkdir(exist_ok=True)

    def test_single_summary(self, 
                           talk_id: str,
                           query: str,
                           files: List[Path] = None,
                           file_ids: List[str] = None,
                           history: list = None) -> Optional[Dict]:
        """测试单次摘要生成"""
        # 准备文件数据
        files_data = []
        if files:
            for file_path in files:
                files_data.append(
                    ("files", (file_path.name, open(file_path, "rb"), "text/plain"))
                )
        
        # 准备表单数据
        data = {
            "talk_id": talk_id,
            "query": query,
            "history": history or []  # 序列化为JSON字符串
        }
        
        if file_ids:
            data["file_ids"] = file_ids
        
        try:
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/chat_summary_2",
                files=files_data,
                data=data,
                timeout=120  # 摘要生成可能需要更长时间
            )
            end_time = time.time()
            
            # 关闭所有文件流
            for _, file_tuple in files_data:
                file_tuple[1].close()
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 请求成功 (耗时: {end_time - start_time:.2f}s)")
                print(f"   状态: {data['status']}")
                print(f"   回答: {data['answer']}..." if data.get('answer') else "   无回答")
                print(f"   参考: {data['reference']}")
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

def main():
    # 创建测试器实例
    tester = ChatSummaryTester("http://localhost:10081")  # 修改为实际接口地址
    
    # 运行单个测试示例
    print("单个测试示例:")
    base_dir = Path("tests/docs/")
    test_files = [base_dir / "1.pdf", base_dir / "2.docx", base_dir / "3.txt"]
    talk_id = f"single_test_2"
    # history = [
    #     {"role": "user", "content": "什么是自然语言处理？"},
    #     {"role": "assistant", "content": "自然语言处理是人工智能的一个分支，专注于计算机与人类语言的交互。"}
    # ]
    
    result = tester.test_single_summary(
        talk_id=talk_id,
        query="总结一下中兴电子文档的内容",
        files=test_files,  # 只使用第一个测试文件
        file_ids=["001","002","003"],
        # history=history
    )
    
    # 运行全面测试
    # tester.run_comprehensive_test()

if __name__ == "__main__":
    main()