import requests
import os

def test_upload_file():
    # 接口URL
    url = "http://localhost:10081/upload"  # 替换为您的实际URL
    
    # 准备文件
    file_path = "tests/docs/【兴证电子】世运电路2023中报点评.pdf"  # 替换为您的测试文件路径
    
    # 如果测试文件不存在，创建一个
    # if not os.path.exists(file_path):
    #     with open(file_path, "w") as f:
    #         f.write("这是一个测试文件内容")
    
    # 准备表单数据
    files = {"file": open(file_path, "rb")}
    data = {"file_id": "testpdf001"}  # 替换为您想要的file_id
    
    try:
        # 发送POST请求
        response = requests.post(url, files=files, data=data)
        
        # 打印响应
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
        
        # 关闭文件
        files["file"].close()
        
        return response
    except Exception as e:
        print(f"请求出错: {e}")
        return None

# 运行测试
if __name__ == "__main__":
    test_upload_file()