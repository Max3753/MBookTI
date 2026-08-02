import type { TheaterScene } from "../types/mbtiTest";

const img = (name: string) => new URL(`./mbti_test_img/${name}`, import.meta.url).href

export const theaterScripts: TheaterScene[] = [
    // ==================== 入口场景 ====================
    {
        id: 'proj_start',
        title: '老板的突然通知',
        emoji: '🏢',
        image: img('proj_start.jpeg'),
        dialogue: '老板：“原计划取消，明天要新方案。”',
        options: [
        {
            text: '立刻打开文档，列出步骤清单',
            next: 'proj_j_branch',
            scores: { J: 1 }
        },
        {
            text: '先放一放，去喝杯咖啡让想法飞一会儿',
            next: 'proj_p_branch',
            scores: { P: 1 }
        },
        ],
    },

    // ==================== J 分支（判断型路径）====================
    {
        id: 'proj_j_branch',
        title: '进入执行模式',
        emoji: '📋',
        image: img('proj_j_path.jpeg'),
        dialogue: '你很快理清了思路，两个方案轮廓浮现。一个稳妥但保守，另一个新颖但冒险。',
        options: [
        {
            text: '列出两张方案的利弊对比表，用数据决策',
            next: 'proj_j_tf',
            scores: { T: 1 }
        },
        {
            text: '问自己“哪个更贴合团队的价值观？”再做决定',
            next: 'proj_j_tf',
            scores: { F: 1 }
        },
        ],
    },
    {
        id: 'proj_j_tf',
        title: '方案的选择',
        emoji: '📊',
        image: img('proj_j_f.jpeg'),
        dialogue: '你选定了方案。现在需要向客户说明核心逻辑。时间紧迫，你会怎么准备？',
        options: [
        {
            text: '制作逻辑缜密的流程图和要点清单，确保无懈可击',
            next: 'proj_j_end',
            scores: { T: 1, J: 1 }
        },
        {
            text: '构思一个能引起共鸣的故事，把价值用情感包装',
            next: 'proj_j_end',
            scores: { F: 1, J: 1 }
        },
        ],
    },
    {
        id: 'proj_j_end',
        title: '准备就绪',
        emoji: '✅',
        image: img('proj_j_t.jpeg'),
        dialogue: '你整理好所有材料，看了一眼时钟，对自己说：“可以了。”',
        options: [
        {
            text: '关掉电脑，奖励自己一杯热茶',
            next: 'end',
            scores: {}
        },
        ],
    },

    // ==================== P 分支（感知型路径）====================
    {
        id: 'proj_p_branch',
        title: '灵感漫游',
        emoji: '☕',
        image: img('proj_p_n.jpeg'),
        dialogue: '喝咖啡时你随手翻着行业动态，一个跨界玩法的念头突然击中了你。',
        options: [
        {
            text: '深入研究这个跨界案例的具体数据和操作细节',
            next: 'proj_p_sn',
            scores: { S: 1 }
        },
        {
            text: '顺着这个灵感立刻脑暴出更多天马行空的变体',
            next: 'proj_p_sn',
            scores: { N: 1 }
        },
        ],
    },
    {
        id: 'proj_p_sn',
        title: '创意的岔路口',
        emoji: '💡',
        image: img('proj_p_path.jpeg'),
        dialogue: '你的草稿纸上已经画满了疯狂的念头，但现在需要落地成一个具体方案。',
        options: [
        {
            text: '筛选出最有操作性的那个，开始搭建框架',
            next: 'proj_p_end',
            scores: { S: 1, J: 1 }
        },
        {
            text: '保留几个最喜欢的点，让它们在展示时自然流动',
            next: 'proj_p_end',
            scores: { N: 1, P: 1 }
        },
        ],
    },
    {
        id: 'proj_p_end',
        title: '灵感成型',
        emoji: '🎨',
        image: img('proj_p_s.jpeg'),
        dialogue: '你看着眼前的成果，虽然不完美，但充满了惊喜的火花。',
        options: [
        {
            text: '就是它了！直接去演示，边讲边发挥',
            next: 'end',
            scores: {}
        },
        ],
    },
];
