import google.genai as genai
from google.genai import types
import os



Model=os.getenv("GEMINI_MODEL") 
key =os.getenv('GOOGLE_API_KEY')
  




"""
client = genai.Client(
    api_key='AIzaSyBmwRNny4vNwpiSs7sNZzS43WpD-uqn6Xk',
    http_options=types.HttpOptions(api_version='v1'))

## 💬 生成内容

### 基础文本生成





response = client.models.generate_content(
    model='gemini-2.0-pro',
    contents='为什么天空是蓝色的？'
)
print(response.text)
"""