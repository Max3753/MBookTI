# AI 推荐书目
from openai import AsyncOpenAI
from app.config import settings

MBTI_PROFILES = {
    "INTJ": {"traits": ["战略思维", "独立", "理性", "完美主义"], "reading_style": "喜欢系统性的、有深度的非虚构类书籍", "genres": ["科学", "哲学", "战略", "科幻"]},
    "INTP": {"traits": ["逻辑", "分析", "创新", "理论"], "reading_style": "喜欢探索理论和概念的书籍", "genres": ["科学", "技术", "哲学"]},
    "ENTJ": {"traits": ["领导力", "效率", "决断", "目标导向"], "reading_style": "喜欢实用性和战略性的书籍", "genres": ["商业", "传记", "战略"]},
    "ENTP": {"traits": ["辩论", "创新", "灵活", "好奇心"], "reading_style": "喜欢跨学科和挑战思维的书籍", "genres": ["科技", "推理", "跨学科"]},
    "INFJ": {"traits": ["洞察力", "理想主义", "深度", "利他"], "reading_style": "喜欢有深度和意义的书籍", "genres": ["心理学", "哲学", "文学"]},
    "INFP": {"traits": ["理想主义", "创造力", "同理心", "价值驱动"], "reading_style": "喜欢富有诗意和人文关怀的书籍", "genres": ["文学", "诗歌", "心理学"]},
    "ENFJ": {"traits": ["感染力", "利他", "组织", "激励"], "reading_style": "喜欢关于人际关系和自我提升的书籍", "genres": ["自我提升", "人际关系", "传记"]},
    "ENFP": {"traits": ["热情", "创造力", "好奇心", "社交"], "reading_style": "喜欢启发性和富有想象力的书籍", "genres": ["心理学", "小说", "创意"]},
    "ISTJ": {"traits": ["可靠", "责任", "传统", "细致"], "reading_style": "喜欢事实性和结构化的书籍", "genres": ["历史", "实用手册", "纪实"]},
    "ISFJ": {"traits": ["体贴", "忠诚", "务实", "细心"], "reading_style": "喜欢温暖和实用的书籍", "genres": ["生活", "健康", "家庭"]},
    "ESTJ": {"traits": ["执行力", "秩序", "效率", "务实"], "reading_style": "喜欢高效和实用的书籍", "genres": ["管理", "经济", "实用"]},
    "ESFJ": {"traits": ["友善", "合作", "尽责", "传统"], "reading_style": "喜欢关于社交和生活的书籍", "genres": ["社交", "健康", "生活"]},
    "ISTP": {"traits": ["冷静", "动手", "灵活", "探索"], "reading_style": "喜欢动手实践和探索类的书籍", "genres": ["技术", "冒险", "工艺"]},
    "ISFP": {"traits": ["敏感", "艺术", "和谐", "行动"], "reading_style": "喜欢艺术和美学相关的书籍", "genres": ["艺术", "旅行", "摄影"]},
    "ESTP": {"traits": ["精力", "冒险", "务实", "灵活"], "reading_style": "喜欢刺激和实用的书籍", "genres": ["冒险", "商业", "运动"]},
    "ESFP": {"traits": ["热情", "表现", "社交", "乐观"], "reading_style": "喜欢娱乐和艺术类的书籍", "genres": ["娱乐", "艺术", "旅行"]},
}

class AIRecommender:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_api_url
        )
        self.model = settings.deepseek_model
        
    async def recommend(self, mbti_code: str, count: int = 5) -> list[dict]:
        """调用 AI 推荐书目"""
        profile = MBTI_PROFILES.get(mbti_code.upper())
        if not profile:
            raise ValueError(f"未知的 MBTI 类型: {mbti_code}")
        
        prompt = f"""
你是一位专业的阅读顾问。用户的MBTI类型是 {mbti_code}。

该类型核心特质：{', '.join(profile['traits'])}。
阅读偏好：{profile['reading_style']}。

请推荐 {count} 本最适合该类型的书籍。
要求：
1. 优先推荐中文译本或华语作者的作品
2. 书籍必须真实存在，不要虚构
3. 每本书的推荐理由要结合 MBTI 特质具体说明

以 JSON 格式返回（不要 markdown 代码块）：
{{
  "books": [
    {{
      "title": "书名",
      "author": "作者",
      "description": "内容简介（50-100字）",
      "reasoning": "推荐理由（80-150字，结合MBTI特质）",
      "genre": "类别"
    }}
  ]
}}
"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        import json
        content = response.choices[0].message.content
        return json.loads(content).get("books", [])

