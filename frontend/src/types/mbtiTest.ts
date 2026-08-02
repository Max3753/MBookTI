// 8 维分数对象
export interface MBTIScores {
    E: number; I: number;
    S: number; N: number;
    T: number; F: number;
    J: number; P: number;
}

// 测试阶段状态机
export type TestPhase = 'intro' | 'imagePick' | 'theater' | 'result';

// 图片快选题：左右各带一个计分维度键
export interface ImageOption {
    emoji: string; // 占位：之后可替换为 img url
    label: string; // 占位：之后可去除
    image?: string; // 实际图片资源 URL（来自 mbti_test_img/）
    score: keyof MBTIScores; // 点击后加到哪个维度
}

export interface ImageQuestion {
    id: string;
    dimension: 'EI' | 'SN' | 'TF' | 'JP'; // 所属维度
    left: ImageOption;
    right: ImageOption;
}

// 剧场场景
export interface TheaterOption {
    text: string;   // 选项文案
    next: string; // 下一个场景 id，用 'end' 表示结束
    scores: Partial<MBTIScores>; // 选择后加的分
}

export interface TheaterScene {
    id: string;
    title: string;  // 场景标题
    emoji: string; // 占位：之后可替换为 img url
    image?: string; // 实际场景图片资源 URL（来自 mbti_test_img/）
    dialogue: string; // 对话内容
    options: TheaterOption[]; // 选项
}

// 16 型"三个一"反馈
export interface TypeFeedback {
    type: string; // 16 型之一
    metaphor: string; // 类型隐喻,你像...
    blindSpot: string; // 类型盲点,你容易...
    manual: string; // 类型手册,相处建议,你适合...
}
