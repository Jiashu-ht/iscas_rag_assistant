import os
import pdfplumber
from docx import Document

def parse_pdf(file_path):
    """解析PDF文件并返回文本内容"""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"解析PDF文件 {file_path} 时出错: {str(e)}")
    return text

def parse_docx(file_path):
    """解析DOCX文件并返回文本内容"""
    text = ""
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"解析DOCX文件 {file_path} 时出错: {str(e)}")
    return text

def parse_txt(file_path):
    """解析TXT文件并返回文本内容"""
    text = ""
    try:
        # 尝试不同的编码方式读取
        encodings = ['utf-8', 'gbk', 'latin-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()
                break
            except UnicodeDecodeError:
                continue
    except Exception as e:
        print(f"解析TXT文件 {file_path} 时出错: {str(e)}")
    return text

def parse_documents(doc_names, base_dir="."):
    """
    解析多个文档并返回拼接后的文本
    
    参数:
        doc_names: 文档名称列表
        base_dir: 文档存储的基础目录，默认为当前目录
    
    返回:
        所有文档解析后的文本，格式为"文档名称: 文本内容"，用----分隔每个文档
    """
    result = []
    
    for doc_name in doc_names:
        # 构建完整的文件路径
        file_path = os.path.join(base_dir, doc_name)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件 {file_path} 不存在")
            continue
        
        # 根据文件扩展名选择相应的解析函数
        if doc_name.lower().endswith('.pdf'):
            content = parse_pdf(file_path)
        elif doc_name.lower().endswith('.docx'):
            content = parse_docx(file_path)
        elif doc_name.lower().endswith('.txt'):
            content = parse_txt(file_path)
        else:
            print(f"不支持的文件格式: {doc_name}")
            continue
        
        # 添加到结果列表
        result.append(f"文档名称：{doc_name}\n文档内容：{content}")
    
    # 用----连接所有文档内容
    return "\n\n----\n\n".join(result)

# 示例用法
if __name__ == "__main__":
    # 要解析的文档列表
    documents = ["1.pdf", "2.docx", "3.txt"]
    
    # 解析文档并获取结果
    parsed_text = parse_documents(documents, "./tests/docs/")
    
    # 打印结果
    print(parsed_text)
    
    # 可选：将结果保存到文件
    with open("parsed_results.txt", "w", encoding="utf-8") as f:
        f.write(parsed_text)
