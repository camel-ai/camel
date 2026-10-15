# CAMEL Deployment Guide | CAMEL 部署指南

[English](#english) | [中文](#中文)

# English

## Table of Contents
- [Quick Start](#quick-start)
- [Deployment Platforms](#deployment-platforms)
  - [E2B Deployment](#e2b-deployment)
- [Configuration](#configuration)
- [FAQ](#faq)

## Quick Start

1. Install dependencies
```bash
pip install camel-ai[deploy]
```

2. Basic usage
```python
import asyncio
from camel.deploy import DeployToolkit

async def main():
    deploy = DeployToolkit(
        platform="e2b",
        config={
            "api_key": "your_e2b_api_key",
            "project_name": "camel-demo",
            "runtime": "python3.9"
        }
    )
    
    result = await deploy.deploy()
    print(f"Deployment URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Deployment Platforms

### E2B Deployment

E2B is a platform focused on AI application deployment, providing sandbox environments and WebSocket support.

#### Prerequisites
- Python 3.7+
- E2B API key
- Project's requirements.txt file

#### Configuration
```python
config = {
    "api_key": "your_e2b_api_key",      # E2B API key
    "project_name": "camel-demo",        # Project name
    "runtime": "python3.9",              # Python runtime version
    "requirements_path": "requirements.txt",  # Dependencies file path
    "app_path": "app.py"                 # Application entry file
}
```

#### Deployment Steps
1. Get E2B API key
   - Visit [E2B Console](https://e2b.dev)
   - Register/Login
   - Create new API key

2. Prepare project files
   - Ensure requirements.txt exists
   - Prepare entry file (app.py)

3. Execute deployment
```python
deploy = DeployToolkit(platform="e2b", config=config)
result = await deploy.deploy()
```

## Configuration

### Common Configuration
```python
{
    "platform": "e2b",          # Deployment platform
    "project_name": str,        # Project name
    "requirements_path": str,   # Dependencies file path
    "app_path": str            # Application entry file path
}
```

### E2B Specific Configuration
```python
{
    "api_key": str,            # E2B API key
    "runtime": str,            # Python runtime version
    "timeout": int,            # Deployment timeout (seconds)
    "env_vars": dict          # Environment variables
}
```

## FAQ

### 1. Deployment Failed
- Check if API key is correct
- Confirm dependencies file exists and is correct
- Check network connection

### 2. Application Start Failed
- Check if entry file exists
- Confirm all dependencies are installed correctly
- Check application logs for detailed error messages

### 3. Connection Timeout
- Check network connection
- Consider increasing timeout
- Confirm E2B service status

### 4. Resource Cleanup
```python
# Destroy deployment
await deploy.destroy(session_id)
```

---

# 中文

## 目录
- [快速开始](#快速开始-1)
- [部署平台](#部署平台)
  - [E2B 部署](#e2b-部署)
- [配置说明](#配置说明)
- [常见问题](#常见问题)

## 快速开始

1. 安装依赖
```bash
pip install camel-ai[deploy]
```

2. 基本使用
```python
import asyncio
from camel.deploy import DeployToolkit

async def main():
    deploy = DeployToolkit(
        platform="e2b",
        config={
            "api_key": "your_e2b_api_key",
            "project_name": "camel-demo",
            "runtime": "python3.9"
        }
    )
    
    result = await deploy.deploy()
    print(f"部署 URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 部署平台

### E2B 部署

E2B 是一个专注于 AI 应用部署的平台，提供了沙箱环境和 WebSocket 支持。

#### 前置要求
- Python 3.7+
- E2B API 密钥
- 项目的 requirements.txt 文件

#### 配置说明
```python
config = {
    "api_key": "your_e2b_api_key",      # E2B API 密钥
    "project_name": "camel-demo",        # 项目名称
    "runtime": "python3.9",              # Python 运行时版本
    "requirements_path": "requirements.txt",  # 依赖文件路径
    "app_path": "app.py"                 # 应用入口文件
}
```

#### 部署步骤
1. 获取 E2B API 密钥
   - 访问 [E2B 控制台](https://e2b.dev)
   - 注册/登录账号
   - 创建新的 API 密钥

2. 准备项目文件
   - 确保有 requirements.txt
   - 准备应用入口文件 (app.py)

3. 执行部署
```python
deploy = DeployToolkit(platform="e2b", config=config)
result = await deploy.deploy()
```

## 配置说明

### 通用配置
```python
{
    "platform": "e2b",          # 部署平台
    "project_name": str,        # 项目名称
    "requirements_path": str,   # 依赖文件路径
    "app_path": str            # 应用入口文件路径
}
```

### E2B 特定配置
```python
{
    "api_key": str,            # E2B API 密钥
    "runtime": str,            # Python 运行时版本
    "timeout": int,            # 部署超时时间（秒）
    "env_vars": dict          # 环境变量
}
```

## 常见问题

### 1. 部署失败
- 检查 API 密钥是否正确
- 确认依赖文件存在且内容正确
- 查看网络连接是否正常

### 2. 应用启动失败
- 检查入口文件是否存在
- 确认所有依赖都已正确安装
- 查看应用日志获取详细错误信息

### 3. 连接超时
- 检查网络连接
- 考虑增加超时时间
- 确认 E2B 服务状态

### 4. 资源清理
```python
# 销毁部署
await deploy.destroy(session_id)
```

## 更多资源
- [E2B 官方文档](https://e2b.dev/docs)
- [CAMEL GitHub 仓库](https://github.com/camel-ai/camel)
- [问题反馈](https://github.com/camel-ai/camel/issues) 