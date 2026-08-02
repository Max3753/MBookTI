import type { ImageQuestion } from '../types/mbtiTest'

const img = (name: string) => new URL(`./mbti_test_img/${name}`, import.meta.url).href

export const testQuestions: ImageQuestion[] = [
    // ========================
    // EI 维度（精力来源）
    // ========================
    {
        id: 'ei_1',
        dimension: 'EI',
        left:  { emoji: '🎉', label: '热闹聚会', image: img('ei_1_l.jpeg'), score: 'E' },
        right: { emoji: '📚', label: '独自阅读', image: img('ei_1_r.jpeg'), score: 'I' }
    },
    {
        id: 'ei_2',
        dimension: 'EI',
        left:  { emoji: '💬', label: '群聊秒回', image: img('ei_2_l.jpeg'), score: 'E' },
        right: { emoji: '🤔', label: '斟酌后回', image: img('ei_2_r.jpeg'), score: 'I' }
    },
    {
        id: 'ei_3',
        dimension: 'EI',
        left:  { emoji: '🤝', label: '团队项目', image: img('ei_3_l.jpeg'), score: 'E' },
        right: { emoji: '🧑‍💻', label: '独立任务', image: img('ei_3_r.jpeg'), score: 'I' }
    },

    // ========================
    // SN 维度（认知方式）
    // ========================
    {
        id: 'sn_1',
        dimension: 'SN',
        left:  { emoji: '🗺️', label: '看地图找路', image: img('sn_1_l.jpeg'), score: 'S' },
        right: { emoji: '🧭', label: '凭感觉走', image: img('sn_1_r.jpeg'), score: 'N' }
    },
    {
        id: 'sn_2',
        dimension: 'SN',
        left:  { emoji: '📖', label: '先看说明书', image: img('sn_2_l.jpeg'), score: 'S' },
        right: { emoji: '🔧', label: '直接上手试', image: img('sn_2_r.jpeg'), score: 'N' }
    },
    {
        id: 'sn_3',
        dimension: 'SN',
        left:  { emoji: '🔍', label: '细节特写', image: img('sn_3_l.jpeg'), score: 'S' },
        right: { emoji: '🌌', label: '氛围意境', image: img('sn_3_r.jpeg'), score: 'N' }
    },

    // ========================
    // TF 维度（决策依据）
    // ========================
    {
        id: 'tf_1',
        dimension: 'TF',
        left:  { emoji: '⚖️', label: '公正指出错误', image: img('tf_1_l.jpeg'), score: 'T' },
        right: { emoji: '💝', label: '先安抚情绪', image: img('tf_1_r.jpeg'), score: 'F' }
    },
    {
        id: 'tf_2',
        dimension: 'TF',
        left:  { emoji: '📊', label: '看数据报表', image: img('tf_2_l.jpeg'), score: 'T' },
        right: { emoji: '✨', label: '听内心直觉', image: img('tf_2_r.jpeg'), score: 'F' }
    },
    {
        id: 'tf_3',
        dimension: 'TF',
        left:  { emoji: '🧠', label: '坚持逻辑辩论', image: img('tf_3_l.jpeg'), score: 'T' },
        right: { emoji: '🕊️', label: '维护气氛和谐', image: img('tf_3_r.jpeg'), score: 'F' }
    },

    // ========================
    // JP 维度（生活态度）
    // ========================
    {
        id: 'jp_1',
        dimension: 'JP',
        left:  { emoji: '📋', label: '详细行程表', image: img('jp_1_l.jpeg'), score: 'J' },
        right: { emoji: '🎲', label: '随性出发', image: img('jp_1_r.jpeg'), score: 'P' }
    },
    {
        id: 'jp_2',
        dimension: 'JP',
        left:  { emoji: '🗂️', label: '桌面分类整齐', image: img('jp_2_l.jpeg'), score: 'J' },
        right: { emoji: '🎨', label: '创意小堆堆', image: img('jp_2_r.jpeg'), score: 'P' }
    },
    {
        id: 'jp_3',
        dimension: 'JP',
        left:  { emoji: '⏰', label: '提前交卷', image: img('jp_3_l.jpeg'), score: 'J' },
        right: { emoji: '🔥', label: '死线冲刺', image: img('jp_3_r.jpeg'), score: 'P' }
    }
];
