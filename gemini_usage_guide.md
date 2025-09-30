# Google Gemini API 使用指南

## 📦 安装

```bash
pip install google-genai
```

## 🔧 基础配置

### 1. 导入库

```python
from google import genai
from google.genai import types
```

### 2. 创建客户端

#### 使用 Gemini Developer API

```python
# 方法1：直接传入 API Key
client = genai.Client(api_key='YOUR_GEMINI_API_KEY')

# 方法2：使用环境变量
# export GOOGLE_API_KEY='your-api-key'
client = genai.Client()
```

#### 使用 Vertex AI

```python
# 方法1：直接传入参数
client = genai.Client(
    vertexai=True,
    project='your-project-id',
    location='us-central1'
)

# 方法2：使用环境变量
# export GOOGLE_GENAI_USE_VERTEXAI=true
# export GOOGLE_CLOUD_PROJECT='your-project-id'
# export GOOGLE_CLOUD_LOCATION='us-central1'
client = genai.Client()
```

### 3. API 版本设置

```python
# 设置为 v1 稳定版（默认为 beta）
client = genai.Client(
    api_key='YOUR_API_KEY',
    http_options=types.HttpOptions(api_version='v1')
)
```

## 💬 生成内容

### 基础文本生成

```python
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='为什么天空是蓝色的？'
)
print(response.text)
```

### 流式生成

```python
for chunk in client.models.generate_content_stream(
    model='gemini-2.0-flash-001',
    contents='讲一个300字的故事'
):
    print(chunk.text, end='')
```

### 异步生成

```python
# 非流式
response = await client.aio.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='你好'
)

# 流式
async for chunk in await client.aio.models.generate_content_stream(
    model='gemini-2.0-flash-001',
    contents='讲个故事'
):
    print(chunk.text, end='')
```

## 🎯 高级配置

### 系统指令和参数设置

```python
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='high',
    config=types.GenerateContentConfig(
        system_instruction='我说 high，你说 low',
        max_output_tokens=100,
        temperature=0.3,
        top_p=0.95,
        top_k=20,
        candidate_count=1,
        seed=5,
        stop_sequences=['停止！'],
        presence_penalty=0.0,
        frequency_penalty=0.0,
    ),
)
```

### 安全设置

```python
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='你的问题',
    config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category='HARM_CATEGORY_HATE_SPEECH',
                threshold='BLOCK_ONLY_HIGH',
            )
        ]
    ),
)
```

## 🖼️ 多模态输入

### 使用图片（从 GCS）

```python
from google.genai import types

response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents=[
        '这张图片是关于什么的？',
        types.Part.from_uri(
            file_uri='gs://generativeai-downloads/images/scones.jpg',
            mime_type='image/jpeg',
        ),
    ],
)
```

### 使用本地图片

```python
with open('your_image.jpg', 'rb') as f:
    image_bytes = f.read()

response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents=[
        '描述这张图片',
        types.Part.from_bytes(
            data=image_bytes,
            mime_type='image/jpeg'
        ),
    ],
)
```

### 上传文件（仅 Gemini Developer API）

```python
# 上传文件
file = client.files.upload(file='document.pdf')

# 使用文件
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents=['总结这个文件', file]
)
```

## 🔧 函数调用

### 自动函数调用

```python
def get_weather(location: str) -> str:
    """获取当前天气
    
    Args:
        location: 城市和州，例如：北京，中国
    """
    return '晴天'

response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='波士顿的天气怎么样？',
    config=types.GenerateContentConfig(
        tools=[get_weather],
    ),
)
print(response.text)
```

### 手动声明函数

```python
function = types.FunctionDeclaration(
    name='get_weather',
    description='获取指定位置的当前天气',
    parameters=types.Schema(
        type='OBJECT',
        properties={
            'location': types.Schema(
                type='STRING',
                description='城市和州，例如：北京，中国',
            ),
        },
        required=['location'],
    ),
)

tool = types.Tool(function_declarations=[function])

response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='波士顿的天气怎么样？',
    config=types.GenerateContentConfig(tools=[tool]),
)
```

### 禁用自动函数调用

```python
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='波士顿的天气怎么样？',
    config=types.GenerateContentConfig(
        tools=[get_weather],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    ),
)
```

## 📝 JSON 输出

### 使用 Pydantic 模型

```python
from pydantic import BaseModel

class CountryInfo(BaseModel):
    name: str
    population: int
    capital: str
    continent: str

response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='提供美国的信息',
    config=types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema=CountryInfo,
    ),
)
```

### 使用字典定义 Schema

```python
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='提供美国的信息',
    config=types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema={
            'type': 'OBJECT',
            'required': ['name', 'population', 'capital'],
            'properties': {
                'name': {'type': 'STRING'},
                'population': {'type': 'INTEGER'},
                'capital': {'type': 'STRING'},
            },
        },
    ),
)
```

## 💭 多轮对话

### 基础用法

```python
# 创建聊天会话
chat = client.chats.create(model='gemini-2.0-flash-001')

# 发送消息
response1 = chat.send_message('给我讲个故事')
print(response1.text)

# 继续对话
response2 = chat.send_message('用一句话总结这个故事')
print(response2.text)

# 流式对话
for chunk in chat.send_message_stream('继续'):
    print(chunk.text, end='')
```

### 带配置参数的聊天

```python
# 创建带配置的聊天会话
chat = client.chats.create(
    model='gemini-2.0-flash-001',
    config=types.GenerateContentConfig(
        system_instruction='你是一个专业的编程助手，擅长 Python 开发',
        temperature=0.7,
        max_output_tokens=2048,
        top_p=0.95,
        top_k=40,
        safety_settings=[
            types.SafetySetting(
                category='HARM_CATEGORY_HATE_SPEECH',
                threshold='BLOCK_MEDIUM_AND_ABOVE',
            )
        ],
    ),
)

# 发送消息
response = chat.send_message('如何使用 Python 读取 CSV 文件？')
print(response.text)
```

### 带历史记录创建聊天

```python
# 从已有的对话历史开始
history = [
    types.Content(
        role='user',
        parts=[types.Part.from_text('你好')]
    ),
    types.Content(
        role='model',
        parts=[types.Part.from_text('你好！有什么我可以帮助你的吗？')]
    ),
]

chat = client.chats.create(
    model='gemini-2.0-flash-001',
    history=history,
    config=types.GenerateContentConfig(
        system_instruction='你是一个友好的助手',
        temperature=0.8,
    ),
)

# 继续对话
response = chat.send_message('介绍一下自己')
print(response.text)
```

### 聊天中使用工具/函数调用

```python
def search_web(query: str) -> str:
    """搜索网页
    
    Args:
        query: 搜索关键词
    """
    return f"搜索结果：{query}"

def calculate(expression: str) -> float:
    """计算数学表达式
    
    Args:
        expression: 数学表达式，如 "2+2"
    """
    return eval(expression)

# 创建带工具的聊天
chat = client.chats.create(
    model='gemini-2.0-flash-001',
    config=types.GenerateContentConfig(
        tools=[search_web, calculate],
        system_instruction='你是一个智能助手，可以搜索和计算',
    ),
)

response = chat.send_message('搜索 Python 教程，并计算 25 * 4')
print(response.text)
```

### 聊天中发送多模态内容

```python
# 创建聊天
chat = client.chats.create(model='gemini-2.0-flash-001')

# 发送文本
response1 = chat.send_message('你好')

# 发送图片+文本
response2 = chat.send_message([
    '这是什么？',
    types.Part.from_uri(
        file_uri='gs://path/to/image.jpg',
        mime_type='image/jpeg'
    )
])

# 继续对话
response3 = chat.send_message('详细描述一下')
```

### 异步聊天

```python
# 创建异步聊天
chat = client.aio.chats.create(model='gemini-2.0-flash-001')

# 异步非流式
response = await chat.send_message('你好')
print(response.text)

# 异步流式
async for chunk in await chat.send_message_stream('讲个故事'):
    print(chunk.text, end='')
```

### 访问聊天历史

```python
chat = client.chats.create(model='gemini-2.0-flash-001')

response1 = chat.send_message('我叫小明')
response2 = chat.send_message('我刚才说我叫什么？')

# 查看完整对话历史
print(chat.history)
# 输出包含所有的 user 和 model 消息
```

### 聊天配置完整示例

```python
chat = client.chats.create(
    model='gemini-2.0-flash-001',
    config=types.GenerateContentConfig(
        # 系统指令
        system_instruction='你是一个专业的 AI 助手',
        
        # 生成参数
        temperature=0.9,           # 创造性 (0-2)
        top_p=0.95,               # 核采样
        top_k=40,                 # Top-K 采样
        max_output_tokens=8192,   # 最大输出长度
        candidate_count=1,        # 候选响应数量
        
        # 随机种子（可复现结果）
        seed=42,
        
        # 停止序列
        stop_sequences=['END', '结束'],
        
        # 惩罚参数
        presence_penalty=0.0,     # 存在惩罚 (-2 到 2)
        frequency_penalty=0.0,    # 频率惩罚 (-2 到 2)
        
        # 安全设置
        safety_settings=[
            types.SafetySetting(
                category='HARM_CATEGORY_HARASSMENT',
                threshold='BLOCK_MEDIUM_AND_ABOVE'
            ),
            types.SafetySetting(
                category='HARM_CATEGORY_HATE_SPEECH',
                threshold='BLOCK_MEDIUM_AND_ABOVE'
            ),
        ],
        
        # 响应格式
        response_mime_type='text/plain',  # 或 'application/json'
        
        # 工具配置
        tools=[],  # 函数列表
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode='AUTO'  # 'AUTO', 'ANY', 'NONE'
            )
        ),
    ),
)
```

## 🧮 Token 计数

```python
# 计数 tokens
response = client.models.count_tokens(
    model='gemini-2.0-flash-001',
    contents='为什么天空是蓝色的？',
)
print(response)

# 计算 tokens（仅 Vertex AI）
response = client.models.compute_tokens(
    model='gemini-2.0-flash-001',
    contents='为什么天空是蓝色的？',
)
```

## 🎨 图像生成（Imagen）

### 生成图片

```python
response = client.models.generate_images(
    model='imagen-3.0-generate-002',
    prompt='前景是一把雨伞，背景是雨夜的天空',
    config=types.GenerateImagesConfig(
        number_of_images=1,
        include_rai_reason=True,
        output_mime_type='image/jpeg',
    ),
)
response.generated_images[0].image.show()
```

### 放大图片（仅 Vertex AI）

```python
response2 = client.models.upscale_image(
    model='imagen-3.0-generate-002',
    image=response.generated_images[0].image,
    upscale_factor='x2',
)
```

### 编辑图片（仅 Vertex AI）

```python
from google.genai.types import RawReferenceImage, MaskReferenceImage

raw_ref_image = RawReferenceImage(
    reference_id=1,
    reference_image=response.generated_images[0].image,
)

mask_ref_image = MaskReferenceImage(
    reference_id=2,
    config=types.MaskReferenceConfig(
        mask_mode='MASK_MODE_BACKGROUND',
    ),
)

response3 = client.models.edit_image(
    model='imagen-3.0-capability-001',
    prompt='阳光和晴朗的天空',
    reference_images=[raw_ref_image, mask_ref_image],
)
```

## 🎬 视频生成（Veo）

```python
import time

# 创建视频生成操作
operation = client.models.generate_videos(
    model='veo-2.0-generate-001',
    prompt='一只全息猫以最快速度驾驶',
    config=types.GenerateVideosConfig(
        number_of_videos=1,
        fps=24,
        duration_seconds=5,
        enhance_prompt=True,
    ),
)

# 轮询操作状态
while not operation.done:
    time.sleep(20)
    operation = client.operations.get(operation)

video = operation.result.generated_videos[0].video
video.show()
```

## 🔄 内容嵌入

```python
response = client.models.embed_content(
    model='text-embedding-004',
    contents='为什么天空是蓝色的？',
)
print(response)

# 多个内容与配置
response = client.models.embed_content(
    model='text-embedding-004',
    contents=['为什么天空是蓝色的？', '你多大了？'],
    config=types.EmbedContentConfig(output_dimensionality=10),
)
```

## 💾 缓存管理

```python
# 创建缓存
cached_content = client.caches.create(
    model='gemini-2.0-flash-001',
    config=types.CreateCachedContentConfig(
        contents=[
            types.Content(
                role='user',
                parts=[
                    types.Part.from_uri(
                        file_uri='gs://path/to/file.pdf',
                        mime_type='application/pdf'
                    ),
                ],
            )
        ],
        system_instruction='总结这个 PDF',
        display_name='test cache',
        ttl='3600s',
    ),
)

# 使用缓存生成内容
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='总结 PDF',
    config=types.GenerateContentConfig(
        cached_content=cached_content.name,
    ),
)
```

## 🎓 模型微调（仅 Vertex AI）

```python
# 创建微调任务
tuning_job = client.tunings.tune(
    base_model='gemini-2.0-flash-001',
    training_dataset=types.TuningDataset(
        gcs_uri='gs://path/to/train_data.jsonl',
    ),
    config=types.CreateTuningJobConfig(
        epoch_count=1,
        tuned_model_display_name='my_tuned_model'
    ),
)

# 获取微调任务状态
tuning_job = client.tunings.get(name=tuning_job.name)

# 使用微调后的模型
response = client.models.generate_content(
    model=tuning_job.tuned_model.endpoint,
    contents='你的问题',
)
```

## 📊 批量预测

```python
# 创建批量任务
job = client.batches.create(
    model='gemini-2.0-flash-001',
    src='bq://my-project.my-dataset.my-table',  # 或 gcs://...
)

# 检查任务状态
while job.state not in ['JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED']:
    job = client.batches.get(name=job.name)
    time.sleep(30)

# 列出所有批量任务
for job in client.batches.list():
    print(job)
```

## 🔍 文件管理（仅 Gemini Developer API）

```python
# 上传文件
file = client.files.upload(file='document.pdf')
print(file)

# 获取文件信息
file_info = client.files.get(name=file.name)

# 删除文件
client.files.delete(name=file.name)
```

## 📋 列出模型

```python
# 列出基础模型
for model in client.models.list():
    print(model)

# 使用分页
pager = client.models.list(config={'page_size': 10})
print(pager[0])
pager.next_page()
print(pager[0])

# 列出微调模型
for model in client.models.list(config={'query_base': False}):
    print(model)
```

## ⚠️ 错误处理

```python
from google.genai import errors

try:
    client.models.generate_content(
        model="invalid-model-name",
        contents="你好",
    )
except errors.APIError as e:
    print(f"错误代码: {e.code}")
    print(f"错误信息: {e.message}")
```

## 🌐 代理设置

```bash
# 设置环境变量
export HTTPS_PROXY='http://username:password@proxy_uri:port'
export SSL_CERT_FILE='client.pem'
```

## 🚀 性能优化

### 使用 aiohttp（异步客户端）

```bash
pip install google-genai[aiohttp]
```

```python
http_options = types.HttpOptions(
    async_client_args={'cookies': ..., 'ssl': ...},
)
client = genai.Client(..., http_options=http_options)
```

## 📚 可用模型列表

### 文本生成模型（Gemini 系列）

#### Gemini 2.0 系列
- **`gemini-2.0-flash-exp`** - 最新实验版，速度快，性能强
- **`gemini-2.0-flash-001`** - 稳定版，适合生产环境
- **`gemini-2.0-flash-thinking-exp`** - 带思维链的版本，适合复杂推理

#### Gemini 1.5 系列
- **`gemini-1.5-pro`** - 高性能版本，支持 200 万 token 上下文
- **`gemini-1.5-pro-002`** - Pro 稳定版
- **`gemini-1.5-flash`** - 快速版本，平衡性能和速度
- **`gemini-1.5-flash-002`** - Flash 稳定版
- **`gemini-1.5-flash-8b`** - 轻量级版本，速度更快

#### Gemini 1.0 系列（旧版）
- **`gemini-1.0-pro`** - 第一代 Pro 版本
- **`gemini-1.0-pro-vision`** - 支持视觉输入的版本

### 文本嵌入模型

- **`text-embedding-004`** - 最新的文本嵌入模型（推荐）
- **`text-embedding-preview-0815`** - 预览版嵌入模型
- **`text-multilingual-embedding-002`** - 多语言嵌入模型
- **`embedding-001`** - 基础嵌入模型

### 图像生成模型（Imagen 系列）

- **`imagen-3.0-generate-001`** - Imagen 3.0 生成模型
- **`imagen-3.0-generate-002`** - Imagen 3.0 改进版（推荐）
- **`imagen-3.0-capability-001`** - 图像编辑专用模型
- **`imagen-3.0-fast-generate-001`** - 快速生成版本
- **`imagegeneration@006`** - Vertex AI 版本

### 视频生成模型（Veo 系列）

- **`veo-2.0-generate-001`** - Veo 2.0 视频生成模型
- **`veo-001`** - Veo 第一代模型

### 代码模型

- **`gemini-1.5-pro-code`** - 专门优化的代码生成版本
- **`gemini-1.5-flash-code`** - 快速代码生成版本

### 特殊用途模型

- **`aqa`** - 归因问答模型（Attributed Question Answering）
- **`gemini-1.0-ultra`** - 最强性能版本（限量访问）

### 查看所有可用模型

```python
# 列出所有基础模型
for model in client.models.list():
    print(f"模型名称: {model.name}")
    print(f"显示名称: {model.display_name}")
    print(f"描述: {model.description}")
    print(f"支持的方法: {model.supported_generation_methods}")
    print("-" * 50)

# 列出微调模型
for model in client.models.list(config={'query_base': False}):
    print(model.name)
```

### 模型选择建议

| 使用场景 | 推荐模型 | 说明 |
|---------|---------|------|
| **日常对话** | `gemini-2.0-flash-001` | 速度快，质量高 |
| **复杂推理** | `gemini-1.5-pro-002` | 上下文长，理解能力强 |
| **代码生成** | `gemini-1.5-pro` | 代码能力出色 |
| **快速响应** | `gemini-1.5-flash-8b` | 延迟最低 |
| **长文本处理** | `gemini-1.5-pro` | 支持 200 万 token |
| **多模态理解** | `gemini-2.0-flash-001` | 支持图片、视频、音频 |
| **文本向量化** | `text-embedding-004` | 最新嵌入模型 |
| **图像生成** | `imagen-3.0-generate-002` | 质量最好 |
| **视频生成** | `veo-2.0-generate-001` | 最新视频模型 |

### 模型特性对比

```python
# 获取特定模型的详细信息
model_info = client.models.get(model='gemini-2.0-flash-001')

print(f"模型名称: {model_info.name}")
print(f"版本: {model_info.version}")
print(f"输入 Token 限制: {model_info.input_token_limit}")
print(f"输出 Token 限制: {model_info.output_token_limit}")
print(f"支持的方法: {model_info.supported_generation_methods}")
print(f"温度范围: {model_info.temperature}")
print(f"Top-P 范围: {model_info.top_p}")
print(f"Top-K 范围: {model_info.top_k}")
```



开启搜索
from google import genai
from google.genai import types

client = genai.Client()

grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)

config = types.GenerateContentConfig(
    tools=[grounding_tool]
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Who won the euro 2024?",
    config=config,
)

print(response.text)

### 模型命名规则

- **gemini-X.X** - 版本号（1.0, 1.5, 2.0）
- **-pro** - 高性能版本
- **-flash** - 快速版本
- **-8b** - 参数规模（80 亿参数）
- **-exp** - 实验版本
- **-001, -002** - 迭代版本号

## 📖 参考资源

- 官方文档：https://googleapis.github.io/python-genai/
- GitHub 仓库：https://github.com/googleapis/python-genai
- API 文档：https://ai.google.dev/gemini-api/docs
