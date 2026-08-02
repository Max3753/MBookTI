import type { ImageQuestion } from '../types/mbtiTest'

export const testQuestions: ImageQuestion[] = [
    // ========================
    // EI 维度（精力来源）
    // ========================
    {
        id: 'ei_1',
        dimension: 'EI',
        left:  { emoji: '🎉', label: '热闹聚会', score: 'E' },
        right: { emoji: '📚', label: '独自阅读', score: 'I' }
    },
    {
        id: 'ei_2',
        dimension: 'EI',
        left:  { emoji: '💬', label: '群聊秒回', score: 'E' },
        right: { emoji: '🤔', label: '斟酌后回', score: 'I' }
    },
    {
        id: 'ei_3',
        dimension: 'EI',
        left:  { emoji: '🤝', label: '团队项目', score: 'E' },
        right: { emoji: '🧑‍💻', label: '独立任务', score: 'I' }
    },

    // ========================
    // SN 维度（认知方式）
    // ========================
    {
        id: 'sn_1',
        dimension: 'SN',
        left:  { emoji: '🗺️', label: '看地图找路', score: 'S' },
        right: { emoji: '🧭', label: '凭感觉走', score: 'N' }
    },
    {
        id: 'sn_2',
        dimension: 'SN',
        left:  { emoji: '📖', label: '先看说明书', score: 'S' },
        right: { emoji: '🔧', label: '直接上手试', score: 'N' }
    },
    {
        id: 'sn_3',
        dimension: 'SN',
        left:  { emoji: '🔍', label: '细节特写', score: 'S' },
        right: { emoji: '🌌', label: '氛围意境', score: 'N' }
    },

    // ========================
    // TF 维度（决策依据）
    // ========================
    {
        id: 'tf_1',
        dimension: 'TF',
        left:  { emoji: '⚖️', label: '公正指出错误', score: 'T' },
        right: { emoji: '💝', label: '先安抚情绪', score: 'F' }
    },
    {
        id: 'tf_2',
        dimension: 'TF',
        left:  { emoji: '📊', label: '看数据报表', score: 'T' },
        right: { emoji: '✨', label: '听内心直觉', score: 'F' }
    },
    {
        id: 'tf_3',
        dimension: 'TF',
        left:  { emoji: '🧠', label: '坚持逻辑辩论', score: 'T' },
        right: { emoji: '🕊️', label: '维护气氛和谐', score: 'F' }
    },

    // ========================
    // JP 维度（生活态度）
    // ========================
    {
        id: 'jp_1',
        dimension: 'JP',
        left:  { emoji: '📋', label: '详细行程表', score: 'J' },
        right: { emoji: '🎲', label: '随性出发', score: 'P' }
    },
    {
        id: 'jp_2',
        dimension: 'JP',
        left:  { emoji: '🗂️', label: '桌面分类整齐', score: 'J' },
        right: { emoji: '🎨', label: '创意小堆堆', score: 'P' }
    },
    {
        id: 'jp_3',
        dimension: 'JP',
        left:  { emoji: '⏰', label: '提前交卷', score: 'J' },
        right: { emoji: '🔥', label: '死线冲刺', score: 'P' }
    }
];
