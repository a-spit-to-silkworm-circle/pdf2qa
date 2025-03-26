# PDF2QA - PDF/Word文档转问答数据工具

这个工具可以读取PDF和Word文档，利用DeepSeek API生成用于微调的问答对数据，并以JSON格式输出。

## 功能特点

- 支持PDF和Word文档处理
- 自动分割大型文档以适应API限制
- 使用DeepSeek API生成高质量问答对
- 支持直接文本处理和文件API处理两种方式
- 自动验证生成的JSON格式
- 针对大文件和小文件采用不同的处理策略

## 使用前准备

Python 3.10 

1. 安装依赖：
```bash
# 使用requirements.txt安装所有依赖
pip install -r requirements.txt
```


3. 设置DeepSeek API环境变量：
```bash
export DEEPSEEK_API_KEY="your_api_key_here"
# 可选，如果需要自定义API端点
export DEEPSEEK_API_BASE="https://api.deepseek.com/v1"
```

## 使用方法

1. 将待处理的PDF或Word文件放入`pdf`目录
2. 运行程序
```bash
python main.py
```
3. 生成的txt文件将保存在`output`目录中

## 输出格式

输出的txt文件格式如下：
```
  {"role": "user", "content": "问题1？"},
  {"role": "assistant", "content": "答案1。"},
  {"role": "user", "content": "问题2？"},
  {"role": "assistant", "content": "答案2。"}

```

## 文件大小处理

- 对于小于20MB的文件，程序会提取文本内容，分块处理
- 对于大于20MB的文件，程序会使用DeepSeek的文件API直接处理整个文件

## 注意事项

- DeepSeek API有调用频率限制，程序中设置了延迟以避免超过限制
- 处理大型文件可能需要较长时间，请耐心等待
- 确保网络连接稳定以保证API调用正常

## 自定义配置

可在`main.py`文件中调整以下参数：
- 文本分块大小：`chunk_size`（默认40000字符）
- 分块重叠部分：`chunk_overlap`（默认200字符）
- 文件大小限制：`size_limit_mb`（默认20MB）
- 温度参数：`temperature`（默认0.7）
- 最大输出token：`max_tokens`（默认根据处理模式不同） 