# 项目环境变量配置
from typing import List

from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基本信息
    # 项目名称
    app_name: str = "MBookTI"
    # 项目版本
    app_version: str = "1.0.0"
    # 项目描述
    app_description: str = "根据MBTI人格推荐书籍"
    # 项目作者
    app_author: str = "Max3753"
    
    # 数据库配置（必须通过 .env 或环境变量设置）
    DB_URL: str = ""
    
    # CORS配置
    # 允许跨域访问的域名
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    
    # LLM配置
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY")
    deepseek_api_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    
    # 日志配置
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"    # 忽略未定义的配置项
        
    def get_cors_origins_list(self) -> List[str]:
        """获取CORS允许的源列表"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

settings = Settings()

def get_settings():
    # 获取配置
    return settings

# 验证配置是否完善
def validate_settings():
    # 验证配置是否完善
    errors =[]
    warnings = []
    
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not llm_api_key:
        warnings.append("LLM_API_KEY或OPENAI_API_KEY未配置,LLM功能可能无法使用")
        
    if errors:
        error_msg = "配置错误:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)
    
    if warnings:
        print("\n⚠️  配置警告:")
        for w in warnings:
            print(f"  - {w}")
    
    return True

# 打印配置信息（调试时使用）
def print_config():
    """打印当前配置(隐藏敏感信息)"""
    print(f"应用名称: {settings.app_name}")
    print(f"版本: {settings.app_version}")
    print(f"作者: {settings.app_author}")
    print(f"服务器: {settings.host}:{settings.port}")
    print(f"数据库: {settings.DB_URL}")

    # 检查LLM配置
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    llm_base_url = os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or settings.deepseek_api_url
    llm_model = os.getenv("LLM_MODEL_ID") or os.getenv("DEEPSEEK_MODEL_ID")

    print(f"LLM API Key: {'已配置' if llm_api_key else '未配置'}")
    print(f"LLM Base URL: {llm_base_url}")
    print(f"LLM Model: {llm_model}")
    print(f"日志级别: {settings.log_level}")

# 验证配置是否完善
"""
if __name__ == "__main__":
    print_config()
"""
