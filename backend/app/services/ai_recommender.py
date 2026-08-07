# AI 推荐书目
import json
import logging
import re

from openai import AsyncOpenAI, Timeout
from app.config import settings

logger = logging.getLogger(__name__)

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
            base_url=settings.deepseek_api_url,
            # 超时显式配置：连接 5s / 其余 60s。SDK 默认 600s 会拖死请求（前端 60s 已超时，后端还在等）。
            # 注意 httpx.Timeout 必须带默认值：Timeout(60, connect=5) 即 connect=5、read/write/pool=60
            timeout=Timeout(60, connect=5),
            # SDK 层不自动重试（默认 max_retries=2），重试统一由业务层 recommend() 控制，
            # 避免「SDK 重试 × 业务重试」叠加成最多 9 次实际请求
            max_retries=0,
        )
        self.model = settings.deepseek_model
        # AI 偶发返回格式不完整 JSON：最多重试 2 次，每次都换一个更严格的约束
        self.max_attempts = 3

    @staticmethod
    def _build_prompt(mbti_code: str, profile: dict, count: int, strict: bool = False, exclude_titles: list[str] | None = None, with_reasoning: bool = True) -> str:
        """构建带强 JSON 约束的 prompt。

        strict=True 用于失败重试：进一步收紧输出要求，降低再次格式出错概率。
        exclude_titles：已推荐过/已在库中的书名列表，要求 AI 避开，保证每次生成的书单互相独立。
        with_reasoning=False 用于「候选生成」阶段：只产出书籍数据（title/author/description/genre），
        推荐词在书单确认后单独调用统一生成。
        """
        base = f"""
你是一位专业的阅读顾问。用户的MBTI类型是 {mbti_code}。

该类型核心特质：{', '.join(profile['traits'])}。
阅读偏好：{profile['reading_style']}。

请推荐 {count} 本最适合该类型的书籍。
要求：
1. 优先推荐中文译本或华语作者的作品
2. 书籍必须真实存在，不要虚构
"""
        if with_reasoning:
            base += f"""
3. 每本书的推荐理由要结合 MBTI 特质具体说明
4. 推荐理由必须包含三要素：① 这本书讲什么（点名核心内容/主题）② 读了能获得什么（收益钩子）③ 与 {mbti_code} 特质的关联（为什么适合这个人格）
"""
        if exclude_titles:
            # 排除列表截断保护：书名太多时只列前 60 本，避免 prompt 失控
            names = "、".join(exclude_titles[:60])
            base += f"""
5. 以下书籍已经推荐过或在书库中，请务必**不要重复推荐**其中任何一本（严格避开）：{names}
"""

        book_fields = (
            '      "title": "书名",\n'
            '      "author": "作者",\n'
            '      "description": "内容简介（50-100字）",\n'
        )
        if with_reasoning:
            book_fields += (
                '      "reasoning": "推荐理由（100-180字，必须包含：书讲什么+读完获得什么+与MBTI特质的关联）",\n'
            )
        book_fields += '      "genre": "类别"'

        json_contract = f"""
输出必须是**严格合法的单个 JSON 对象**，不要 markdown 代码块，不要任何前后缀文字、注释或解释。
格式如下（字段名用英文，值用中文）：
{{
  "books": [
    {{
{book_fields}
    }}
  ]
}}
JSON 合法性硬性要求：
- 所有字符串必须用半角双引号包裹，禁止单引号
- 字符串内禁止出现换行符、制表符，长文本请写成一行
- 禁止在 JSON 内部添加注释（// 或 /* */）
- 结尾必须正确闭合 }} 括号
"""
        if strict:
            json_contract += (
                "\n上一轮你输出的 JSON 格式不合法导致解析失败。本次请务必遵守：\n"
                "- 只输出一个完整的 JSON 对象，绝对不要 markdown 代码块（```）\n"
                "- 每个字段都必须成对出现双引号，值内不得换行\n"
                "- 输出前先在心里数一遍大括号是否配对\n"
            )
        return base + json_contract

    @staticmethod
    def _extract_json(content: str):
        """从 AI 输出中提取第一个 JSON 对象，并对内容做轻量清理。"""
        if not content:
            return None
        # 去掉可能混入的控制字符（如 \x00-\x1f），它们会导致 json.loads 失败
        content = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", content)
        m = re.search(r"\{.*\}", content, re.S)
        return m.group(0) if m else None

    async def recommend(self, mbti_code: str, count: int = 5, exclude_titles: list[str] | None = None, with_reasoning: bool = True) -> list[dict]:
        """调用 AI 推荐书目，带格式失败重试（更强约束逐级升级）。

        exclude_titles：已推荐过/已在库中的书名列表，要求 AI 避开（每次生成的书单互相独立）。
        with_reasoning=False：候选生成模式，只产出书籍数据，推荐词由调用方在书单确认后统一生成。
        """
        profile = MBTI_PROFILES.get(mbti_code.upper())
        if not profile:
            raise ValueError(f"未知的 MBTI 类型: {mbti_code}")

        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            prompt = self._build_prompt(
                mbti_code, profile, count,
                strict=attempt > 0,
                exclude_titles=exclude_titles,
                with_reasoning=with_reasoning,
            )
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.5,  # 比 0.7 略收敛，减少随机性导致的格式漂移
                    max_tokens=4096,  # 防 count 较大时输出截断 → JSON 不完整 → 无谓重试
                )
            except Exception as e:
                last_error = RuntimeError(f"AI 服务调用失败: {e}")
                continue  # 网络/服务错误也值得重试

            # token 用量日志：便于统计每次生成的成本（DeepSeek 按 token 计费）
            usage = getattr(response, "usage", None)
            if usage is not None:
                logger.info(
                    "AI 候选生成完成 mbti=%s attempt=%d prompt_tokens=%s completion_tokens=%s total=%s",
                    mbti_code, attempt,
                    getattr(usage, "prompt_tokens", "?"),
                    getattr(usage, "completion_tokens", "?"),
                    getattr(usage, "total_tokens", "?"),
                )

            content = response.choices[0].message.content or ""
            raw = self._extract_json(content)
            if raw is None:
                last_error = RuntimeError("AI 返回内容中没有 JSON")
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                last_error = RuntimeError(f"AI 返回的 JSON 解析失败: {e}")
                continue  # 格式错误 → 用更严格约束重试

            # 字段完整性校验，缺字段的书直接丢弃（不再 KeyError 炸接口）
            required = {"title", "author", "description", "genre"}
            if with_reasoning:
                required.add("reasoning")
            books = [
                b for b in (data.get("books") or [])
                if isinstance(b, dict) and required.issubset(b.keys())
            ]
            if books:
                return books
            last_error = RuntimeError("AI 返回的书籍列表为空或字段不完整")

        raise last_error

