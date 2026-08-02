import { ref, computed } from 'vue'
import type { MBTIScores, TestPhase, TheaterOption } from '../types/mbtiTest'
import { testQuestions } from '../resources/testQuestions'
import { theaterScripts } from '../resources/theaterScripts'
import { typeResults } from '../resources/mbtiFeedback'

// 辅助：计算一对字母中前者的百分比（0~100 数值）
function percentOf(a: number, b: number): number {
    const total = a + b
    if (total === 0) return 50
    return Math.round((a / total) * 100)
}

export function useMBTITest() {
    // ---------- 1. 状态 ----------
    const phase = ref<TestPhase>('intro')
    const scores = ref<MBTIScores>({ E: 0, I: 0, S: 0, N: 0, T: 0, F: 0, J: 0, P: 0 })
    const questionIndex = ref(0)
    const currentSceneId = ref('proj_start')
    const theaterHistory = ref<string[]>([])

    // ---------- 2. 动作 ----------
    function goPhase(p: TestPhase) {
        phase.value = p
    }

    function answerQuestion(side: 'left' | 'right') {
        if (phase.value !== 'imagePick') return
        const q = testQuestions[questionIndex.value]
        scores.value[q[side].score] += 1
        questionIndex.value += 1
        if (questionIndex.value >= testQuestions.length) {
            goPhase('theater')
        }
    }

    function chooseTheaterOption(option: TheaterOption) {
        if (phase.value !== 'theater') return
        for (const key of Object.keys(option.scores) as (keyof MBTIScores)[]) {
            scores.value[key] += option.scores[key]!
        }
        theaterHistory.value.push(option.text)
        if (option.next === 'end') {
            goPhase('result')
        } else {
            currentSceneId.value = option.next
        }
    }                                     // ← chooseTheaterOption 在此关闭

    // ---------- 3. 派生状态 ----------
    const currentScene = computed(() =>
        theaterScripts.find(s => s.id === currentSceneId.value) ?? null
    )

    const result = computed(() => {
        let type = ''
        type += scores.value.E >= scores.value.I ? 'E' : 'I'
        type += scores.value.S >= scores.value.N ? 'S' : 'N'
        type += scores.value.T >= scores.value.F ? 'T' : 'F'
        type += scores.value.J >= scores.value.P ? 'J' : 'P'   // ← J vs P，不是 J vs J

        const detail = {
            EI: percentOf(scores.value.E, scores.value.I),
            SN: percentOf(scores.value.S, scores.value.N),
            TF: percentOf(scores.value.T, scores.value.F),
            JP: percentOf(scores.value.J, scores.value.P),
        }
        return { type, detail }
    })

    const feedback = computed(() => typeResults[result.value.type] ?? null)

    // ---------- 4. 导出（必须有！） ----------
    return {
        phase, scores, questionIndex, currentSceneId, theaterHistory,
        currentScene, result, feedback,
        goPhase, answerQuestion, chooseTheaterOption,
    }
}