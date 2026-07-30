from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MbtiType

MBTI_TYPES = [
    {"code": "INTJ", "name": "建筑师", "name_en": "Architect", "description": "富有想象力和战略性的思想家，一切皆在计划之中", "traits":["战略思维", "独立", "理性", "完美主义"]},
    {"code": "INTP", "name": "逻辑学家", "name_en": "Logician", "description": "具有创造力的发明家，对知识有着永不满足的渴望", "traits": ["逻辑", "分析", "创新", "理论"]},
    {"code": "ENTJ", "name": "指挥官", "name_en": "Commander", "description": "大胆、富有想象力且意志强大的领导者，总能找到或创造解决方法", "traits": ["领导力", "效率", "决断", "目标导向"]},
    {"code": "ENTP", "name": "辩论家", "name_en": "Debater", "description": "聪明好奇的思想者，无法抗拒智力挑战", "traits": ["辩论", "创新", "灵活", "好奇心"]},
    {"code": "INFJ", "name": "提倡者", "name_en": "Advocate", "description": "安静而神秘，同时鼓舞人心且不知疲倦的理想主义者", "traits": ["洞察力", "理想主义", "深度", "利他"]},
    {"code": "INFP", "name": "调停者", "name_en": "Mediator", "description": "诗意、善良的利他主义者，总是热情地为正义事业提供帮助", "traits": ["理想主义", "创造力", "同理心", "价值驱动"]},
    {"code": "ENFJ", "name": "主人公", "name_en": "Protagonist", "description": "富有魅力且鼓舞人心的领导者，有着让听众着迷的能力", "traits": ["感染力", "利他", "组织", "激励"]},
    {"code": "ENFP", "name": "竞选者", "name_en": "Campaigner", "description": "热情、有创造力且善于社交的自由精神，总能找到微笑的理由", "traits": ["热情", "创造力", "好奇心", "社交"]},
    {"code": "ISTJ", "name": "物流师", "name_en": "Logistician", "description": "实际且注重事实的个人，其可靠性不容置疑", "traits": ["可靠", "责任", "传统", "细致"]},
    {"code": "ISFJ", "name": "守卫者", "name_en": "Defender", "description": "非常专注和温暖的守护者，随时准备保护所爱之人", "traits": ["体贴", "忠诚", "务实", "细心"]},
    {"code": "ESTJ", "name": "总经理", "name_en": "Executive", "description": "出色的管理者，在管理事物或人员方面无与伦比", "traits": ["执行力", "秩序", "效率", "务实"]},
    {"code": "ESFJ", "name": "执政官", "name_en": "Consul", "description": "极受欢迎且富有同情心的人，总是热心提供帮助", "traits": ["友善", "合作", "尽责", "传统"]},
    {"code": "ISTP", "name": "鉴赏家", "name_en": "Virtuoso", "description": "大胆且实际的实验者，擅长使用各种工具", "traits": ["冷静", "动手", "灵活", "探索"]},
    {"code": "ISFP", "name": "探险家", "name_en": "Adventurer", "description": "灵活且有魅力的艺术家，时刻准备探索和体验新事物", "traits": ["敏感", "艺术", "和谐", "行动"]},
    {"code": "ESTP", "name": "企业家", "name_en": "Entrepreneur", "description": "聪明、精力充沛且善于感知的人，真心享受冒险和边缘生活", "traits": ["精力", "冒险", "务实", "灵活"]},
    {"code": "ESFP", "name": "表演者", "name_en": "Entertainer", "description": "自发的、精力充沛且热情的表演者，生活在他们周围无处不有的快乐中", "traits": ["热情", "表现", "社交", "乐观"]},
]

async def init_mbti_types(session: AsyncSession):
    """初始化 MBTI 类型数据"""
    result = await session.execute(select(MbtiType).limit(1))
    if result.scalar_one_or_none():
        return # 已经初始化过
    
    for item in MBTI_TYPES:
        mbti_type = MbtiType(**item)
        session.add(mbti_type)
    await session.commit()
