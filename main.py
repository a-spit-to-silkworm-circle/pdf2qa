#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import glob
import time
from typing import List, Dict, Any, Optional, Tuple
import tiktoken
import PyPDF2
import docx
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 配置
PDF_DIR = "pdf"
OUTPUT_DIR = "output"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-4a62205812694c92953aadc2c22161e1")  # 从环境变量获取API密钥
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")  # DeepSeek API基础URL

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 初始化OpenAI客户端，用于调用DeepSeek API
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_API_BASE
)

# PDF文本提取函数
def extract_text_from_pdf(pdf_path: str) -> str:
    """从PDF文件中提取文本内容"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n\n"
            return text
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        return ""

# Word文档文本提取函数
def extract_text_from_docx(docx_path: str) -> str:
    """从Word文档中提取文本内容"""
    try:
        doc = docx.Document(docx_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from DOCX {docx_path}: {e}")
        return ""

# 文本分割函数
def split_text(text: str, chunk_size: int = 40000, chunk_overlap: int = 200) -> List[str]:
    """将大文本分割成更小的块，以适应API的限制"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_text(text)
    return chunks

# 使用DeepSeek API生成QA对
def generate_qa_pairs(text_chunk: str) -> List[Tuple[str, str]]:
    """使用DeepSeek API从文本块中生成问答对"""
    try:
        system_prompt = """你是一个专业的问答对生成助手。请根据提供的文本内容，生成高质量的问答对。
问题应该有实质性，答案应该详细且准确，完全基于提供的文本，使用中文回答。

你的回复必须是一个JSON数组，每个元素是一个包含'question'和'answer'字段的对象，例如：
[
    {"question": "问题1？", "answer": "答案1。"},
    {"question": "问题2？", "answer": "答案2。"}
]

尽量生成5个高质量的问答对。"""
        
        response = client.chat.completions.create(
            model="deepseek-chat",  # 或者是其他DeepSeek支持的模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"以下是一段文本，请根据此内容创建高质量的问答对：\n\n{text_chunk}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=8192
        )
        
        # 解析返回的JSON
        content = response.choices[0].message.content
        try:
            data = json.loads(content)
            qa_pairs = []
            
            # 处理可能的不同返回格式
            if isinstance(data, list):
                # 直接是QA对列表
                qa_list = data
            elif isinstance(data, dict):
                # 可能包装在某个字段中
                if "qa_pairs" in data:
                    qa_list = data["qa_pairs"]
                elif "pairs" in data:
                    qa_list = data["pairs"]
                elif "questions_answers" in data:
                    qa_list = data["questions_answers"]
                else:
                    # 尝试找到包含question/answer的任何数组
                    for key, value in data.items():
                        if isinstance(value, list) and len(value) > 0:
                            if isinstance(value[0], dict) and ("question" in value[0] or "q" in value[0]):
                                qa_list = value
                                break
                    else:
                        qa_list = []
            else:
                qa_list = []
            
            # 统一格式处理
            for qa in qa_list:
                if isinstance(qa, dict):
                    # 提取问题
                    question = qa.get("question", qa.get("q", ""))
                    # 提取答案
                    answer = qa.get("answer", qa.get("a", ""))
                    
                    if question and answer:
                        qa_pairs.append((question, answer))
            
            return qa_pairs
        except Exception as e:
            print(f"JSON解析错误: {e}, 内容: {content[:100]}...")
            return []
    
    except Exception as e:
        print(f"Error generating QA pairs: {e}")
        return []

# 使用DeepSeek文件API处理
def process_with_file_api(file_path: str) -> List[Tuple[str, str]]:
    """使用DeepSeek文件API处理较大的文件"""
    try:
        # 打开并上传文件
        with open(file_path, "rb") as file:
            response = client.files.create(
                file=file,
                purpose="assistants"
            )
            file_id = response.id
        
        # 创建系统提示
        system_prompt = """你是一个专业的问答对生成助手。请根据提供的文档内容，生成高质量的问答对。
问题应该有实质性，答案应该详细且准确，完全基于提供的文档，使用中文回答。

你的回复必须是一个JSON数组，每个元素是一个包含'question'和'answer'字段的对象，例如：
[
    {"question": "问题1？", "answer": "答案1。"},
    {"question": "问题2？", "answer": "答案2。"}
]

尽量生成10个高质量的问答对。"""
        
        # 调用DeepSeek API处理文件
        response = client.chat.completions.create(
            model="deepseek-chat",  # 或者是其他DeepSeek支持的模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请基于上传的文档内容，生成高质量的问答对。"}
            ],
            file_ids=[file_id],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=8192
        )
        
        # 解析返回的JSON
        content = response.choices[0].message.content
        try:
            data = json.loads(content)
            qa_pairs = []
            
            # 处理可能的不同返回格式
            if isinstance(data, list):
                # 直接是QA对列表
                qa_list = data
            elif isinstance(data, dict):
                # 可能包装在某个字段中
                if "qa_pairs" in data:
                    qa_list = data["qa_pairs"]
                elif "pairs" in data:
                    qa_list = data["pairs"]
                elif "questions_answers" in data:
                    qa_list = data["questions_answers"]
                else:
                    # 尝试找到包含question/answer的任何数组
                    for key, value in data.items():
                        if isinstance(value, list) and len(value) > 0:
                            if isinstance(value[0], dict) and ("question" in value[0] or "q" in value[0]):
                                qa_list = value
                                break
                    else:
                        qa_list = []
            else:
                qa_list = []
            
            # 统一格式处理
            for qa in qa_list:
                if isinstance(qa, dict):
                    # 提取问题
                    question = qa.get("question", qa.get("q", ""))
                    # 提取答案
                    answer = qa.get("answer", qa.get("a", ""))
                    
                    if question and answer:
                        qa_pairs.append((question, answer))
            
            return qa_pairs
        except Exception as e:
            print(f"JSON解析错误: {e}, 内容: {content[:100]}...")
            return []
        
        # 删除已上传的文件
        client.files.delete(file_id)
        
    except Exception as e:
        print(f"Error processing file {file_path} with file API: {e}")
        return []

# 检查文件大小是否超过API限制
def is_file_too_large(file_path: str, size_limit_mb: int = 20) -> bool:
    """检查文件大小是否超过API限制"""
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    return file_size_mb > size_limit_mb

# 转换问答对为所需的格式
def convert_to_required_format(qa_pairs: List[Tuple[str, str]]) -> List[Dict[str, str]]:
    """将问答对转换为所需的格式"""
    required_format = []
    for question, answer in qa_pairs:
        required_format.append({"role": "user", "content": question})
        required_format.append({"role": "assistant", "content": answer})
    return required_format

# 写入每行记录的函数
def write_records_to_file(records: List[Dict[str, str]], output_file: str):
    """将记录按每行一条写入文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for record in records:
            # 将每条记录转换为无缩进、无换行的JSON字符串并写入文件
            f.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')

# 主处理函数
def process_documents():
    """处理PDF和Word文档，生成训练数据"""
    # 获取所有PDF和Word文件
    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    docx_files = glob.glob(os.path.join(PDF_DIR, "*.docx"))
    
    # 合并文件列表
    all_files = pdf_files + docx_files
    
    for file_path in all_files:
        print(f"处理文件: {file_path}")
        file_name = os.path.basename(file_path)
        output_file = os.path.join(OUTPUT_DIR, f"{os.path.splitext(file_name)[0]}.txt")
        
        # 如果文件太大，使用文件API
        if is_file_too_large(file_path):
            print(f"文件 {file_name} 太大，使用文件API处理")
            qa_pairs = process_with_file_api(file_path)
            
            if qa_pairs:
                # 转换为所需格式
                formatted_data = convert_to_required_format(qa_pairs)
                # 保存到文件，每行一条记录
                write_records_to_file(formatted_data, output_file)
                print(f"已保存到 {output_file}")
            else:
                print(f"无法从 {file_name} 生成有效的QA对")
            
            # 防止API限制
            time.sleep(2)
            continue
        
        # 提取文本
        if file_path.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        elif file_path.lower().endswith('.docx'):
            text = extract_text_from_docx(file_path)
        else:
            print(f"不支持的文件类型: {file_path}")
            continue
        
        if not text:
            print(f"无法从 {file_name} 提取文本")
            continue
        
        # 分割文本
        text_chunks = split_text(text)
        
        # 生成QA对
        all_qa_pairs = []
        for i, chunk in enumerate(text_chunks):
            print(f"处理文本块 {i+1}/{len(text_chunks)}")
            qa_pairs = generate_qa_pairs(chunk)
            if qa_pairs:
                all_qa_pairs.extend(qa_pairs)
            # 防止API限制
            time.sleep(2)
        
        # 转换为所需格式并保存
        if all_qa_pairs:
            formatted_data = convert_to_required_format(all_qa_pairs)
            write_records_to_file(formatted_data, output_file)
            print(f"已保存到 {output_file}")
        else:
            print(f"无法从 {file_name} 生成有效的QA对")

if __name__ == "__main__":
    if not DEEPSEEK_API_KEY:
        print("请设置DEEPSEEK_API_KEY环境变量")
        exit(1)
    
    process_documents()
    print("处理完成!")
