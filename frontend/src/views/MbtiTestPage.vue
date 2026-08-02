<script setup lang="ts">
import { computed } from 'vue'
import { useMBTITest } from '../composables/useMbtiTest'
import { testQuestions } from '../resources/testQuestions'
import IntroScene from '../components/mbti-test/IntroScene.vue'
import ImagePickScene from '../components/mbti-test/ImagePickScene.vue'
import TheaterScene from '../components/mbti-test/TheaterScene.vue'
import ResultScene from '../components/mbti-test/ResultScene.vue'

const { phase, questionIndex, answerQuestion, currentScene, chooseTheaterOption, result, feedback, goPhase } = useMBTITest()

const currentQuestion = computed(() => testQuestions[questionIndex.value])
</script>

<template>
    <div class="min-h-screen">
        <IntroScene v-if="phase === 'intro'" @start="goPhase('imagePick')" />
        <ImagePickScene v-else-if="phase === 'imagePick'"
            :question="currentQuestion"
            :index="questionIndex"
            :total="testQuestions.length"
            @answer="answerQuestion" />
        <TheaterScene v-else-if="phase === 'theater'"
            :scene="currentScene"
            @choose="chooseTheaterOption" />
        <ResultScene v-else
            :type="result.type"
            :detail="result.detail"
            :feedback="feedback" />
    </div>
</template>