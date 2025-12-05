<template>
	<div class="toefl-writing-container">
		<!-- Header -->
		<header class="header">
			<div class="logo">
				ETS <span style="font-style: normal; margin-left: 5px">TOEFL</span>
			</div>
			<button class="next-btn" @click="handleSubmit">提交</button>
		</header>

		<!-- Info Bar -->
		<div class="info-bar">
			<div class="section-info">Section 1 of 1</div>
			<div class="timer-container">
				<span
					id="timer"
					:style="{ visibility: isTimerHidden ? 'hidden' : 'visible' }"
				>
					{{ formatTime(timeRemaining) }}
				</span>
				<button class="toggle-btn" @click="toggleTimer">
					<span>👁️</span>
					<span>{{ isTimerHidden ? "Show Timer" : "Hide Timer" }}</span>
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="main-container">
			<!-- Left Panel: Professor -->
			<div class="left-panel">
				<div class="instructions">
					<span v-if="questionData">
						Your professor is teaching a class on {{ questionData.subject }}.
						Write a post responding to the professor's question.
					</span>
					<span v-else>Loading question...</span>
					<br /><br />
					<strong>In your response, you should do the following.</strong>
					<ul>
						<li>Express and support your opinion.</li>
						<li>Make a contribution to the discussion in your own words.</li>
					</ul>
					<div style="margin-top: 15px">
						An effective response will contain at least 100 words.
					</div>
				</div>

				<div v-if="questionData" class="professor-section">
					<img
						v-if="questionData.professor.avatar"
						:src="questionData.professor.avatar"
						alt="Professor"
						class="avatar"
					/>
					<div class="name-label">{{ questionData.professor.name }}</div>
				</div>

				<div v-if="questionData" class="professor-text">
					{{ questionData.professor.prompt }}
				</div>
			</div>

			<!-- Right Panel: Students + Input -->
			<div class="right-panel">
				<!-- Student 1 -->
				<div
					v-if="questionData && questionData.students[0]"
					class="student-response"
				>
					<div class="student-info">
						<img
							v-if="questionData.students[0].avatar"
							:src="questionData.students[0].avatar"
							alt="Student 1"
							class="avatar"
						/>
						<div class="name-label" style="font-size: 14px; margin-top: 5px">
							{{ questionData.students[0].name }}
						</div>
					</div>
					<div class="student-text">
						{{ questionData.students[0].response }}
					</div>
				</div>

				<!-- Student 2 -->
				<div
					v-if="questionData && questionData.students[1]"
					class="student-response"
				>
					<div class="student-info">
						<img
							v-if="questionData.students[1].avatar"
							:src="questionData.students[1].avatar"
							alt="Student 2"
							class="avatar"
						/>
						<div class="name-label" style="font-size: 14px; margin-top: 5px">
							{{ questionData.students[1].name }}
						</div>
					</div>
					<div class="student-text">
						{{ questionData.students[1].response }}
					</div>
				</div>

				<!-- Writing Input -->
				<div class="writing-area">
					<div class="toolbar">
						<div class="tools-left">
							<button class="tool-btn primary" @click="execCmd('cut')">
								Cut
							</button>
							<button class="tool-btn secondary" disabled>Paste</button>
							<button class="tool-btn secondary" @click="execCmd('undo')">
								Undo
							</button>
							<button class="tool-btn secondary" @click="execCmd('redo')">
								Redo
							</button>
						</div>
						<div class="word-count-controls">
							<button class="toggle-btn" @click="toggleWordCount">
								👁️
								<span>{{
									isWCHidden ? "Show Word Count" : "Hide Word Count"
								}}</span>
							</button>
							<span
								id="word-count"
								:style="{ visibility: isWCHidden ? 'hidden' : 'visible' }"
							>
								{{ wordCount }}
							</span>
						</div>
					</div>
					<textarea
						id="essay-input"
						v-model="essayText"
						placeholder="Enter your response here..."
						spellcheck="false"
						@input="updateWordCount"
					></textarea>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import { getQuestionData, type QuestionData } from "../api/service";

// 响应式数据
const questionData = ref<QuestionData | null>(null);
const essayText = ref("");
const wordCount = ref(0);
const timeRemaining = ref(600); // 10 minutes in seconds
const isTimerHidden = ref(false);
const isWCHidden = ref(false);
let timerInterval: number | null = null;

// 格式化时间
const formatTime = (seconds: number): string => {
	const minutes = Math.floor(seconds / 60);
	const secs = seconds % 60;
	return `${minutes.toString().padStart(2, "0")}:${secs
		.toString()
		.padStart(2, "0")}`;
};

// 更新字数统计
const updateWordCount = () => {
	const text = essayText.value.trim();
	wordCount.value = text === "" ? 0 : text.split(/\s+/).length;
};

// 切换计时器显示
const toggleTimer = () => {
	isTimerHidden.value = !isTimerHidden.value;
};

// 切换字数统计显示
const toggleWordCount = () => {
	isWCHidden.value = !isWCHidden.value;
};

// 执行命令
const execCmd = (command: string) => {
	const textarea = document.getElementById(
		"essay-input"
	) as HTMLTextAreaElement;
	if (textarea) {
		document.execCommand(command);
		textarea.focus();
	}
};

// 启动计时器
const startTimer = () => {
	if (timerInterval) {
		clearInterval(timerInterval);
	}
	timerInterval = window.setInterval(() => {
		if (timeRemaining.value <= 0) {
			clearInterval(timerInterval!);
			handleSubmit();
			return;
		}
		timeRemaining.value--;
	}, 1000);
};

// 提交作文
const handleSubmit = () => {
	if (timerInterval) {
		clearInterval(timerInterval);
	}
	// 直接提交并转到评分区域
	emit("submit", {
		text: essayText.value,
		wordCount: wordCount.value,
		timeSpent: 600 - timeRemaining.value,
		questionFile: questionFile.value,
	});
};

// 加载题目数据
const loadQuestion = async (file: string = "test.yaml") => {
	try {
		questionData.value = await getQuestionData(file);
	} catch (error) {
		console.error("Failed to load question:", error);
	}
};

// 组件内部管理题目文件
const questionFile = ref("test.yaml");

// 定义props（用于接收初始值）
const props = defineProps<{
	initialQuestionFile?: string;
}>();

// 如果提供了初始值，使用它
if (props.initialQuestionFile) {
	questionFile.value = props.initialQuestionFile;
}

// 监听questionFile变化并加载题目
watch(
	() => questionFile.value,
	(newFile) => {
		if (newFile) {
			loadQuestion(newFile);
		}
	},
	{ immediate: true }
);

// 暴露方法供外部设置题目文件
defineExpose({
	setQuestionFile: (file: string) => {
		questionFile.value = file;
		loadQuestion(file);
	},
});

// 组件挂载
onMounted(() => {
	if (questionFile.value) {
		loadQuestion(questionFile.value);
	}
	startTimer();
});

// 组件卸载
onUnmounted(() => {
	if (timerInterval) {
		clearInterval(timerInterval);
	}
});

// 定义事件
const emit = defineEmits<{
	(
		e: "submit",
		data: {
			text: string;
			wordCount: number;
			timeSpent: number;
			questionFile: string;
		}
	): void;
}>();
</script>

<style>
:root {
	--primary-color: #005652; /* ETS Deep Teal */
	--bg-color: #f4f4f4;
	--text-color: #333;
	--border-radius: 8px;
	--btn-grey: #e0e0e0;
}
</style>

<style scoped>
.toefl-writing-container {
	margin: 0;
	padding: 0;
	font-family: "Arial", sans-serif;
	background-color: var(--bg-color);
	color: var(--text-color);
	height: 100vh;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

/* --- Top Navigation Bar --- */
.header {
	background-color: var(--primary-color);
	height: 70px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 30px;
	color: white;
	flex-shrink: 0;
}

.logo {
	font-size: 24px;
	font-weight: bold;
	font-style: italic;
	display: flex;
	align-items: center;
	gap: 10px;
}

.logo span {
	font-family: serif; /* Mimic ETS font style roughly */
}

.next-btn {
	background-color: white;
	color: var(--primary-color);
	border: none;
	padding: 10px 30px;
	border-radius: 25px;
	font-weight: bold;
	font-size: 16px;
	cursor: pointer;
	display: flex;
	align-items: center;
	gap: 5px;
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.next-btn:hover {
	background-color: #f0f0f0;
}

/* --- Info Bar (Section & Timer) --- */
.info-bar {
	background-color: white;
	height: 50px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 30px;
	border-bottom: 1px solid #ddd;
	flex-shrink: 0;
}

.section-info {
	font-weight: bold;
	color: #444;
}

.timer-container {
	display: flex;
	align-items: center;
	gap: 15px;
	font-weight: bold;
	color: #333;
}

.toggle-btn {
	background: none;
	border: none;
	color: var(--primary-color);
	font-weight: bold;
	cursor: pointer;
	display: flex;
	align-items: center;
	gap: 5px;
	font-size: 14px;
}

/* --- Main Layout --- */
.main-container {
	display: flex;
	flex: 1;
	padding: 20px;
	gap: 20px;
	overflow: hidden;
	max-width: 1600px;
	margin: 0 auto;
	width: 100%;
}

/* Left Panel: Professor */
.left-panel {
	flex: 0.8; /* Slightly narrower than right */
	background: white;
	border-radius: var(--border-radius);
	padding: 25px;
	overflow-y: auto;
	border: 1px solid #ccc;
	display: flex;
	flex-direction: column;
}

.instructions {
	color: #555;
	margin-bottom: 20px;
	font-size: 15px;
	line-height: 1.5;
}

.instructions ul {
	padding-left: 20px;
	margin: 10px 0;
}

.professor-section {
	display: flex;
	flex-direction: column;
	align-items: center;
	margin-bottom: 20px;
}

.avatar {
	width: 80px;
	height: 80px;
	border-radius: 50%;
	object-fit: cover;
	margin-bottom: 10px;
	border: 2px solid #eee;
}

.name-label {
	font-weight: bold;
	font-size: 16px;
	margin-bottom: 15px;
	color: #222;
}

.professor-text {
	font-size: 16px;
	line-height: 1.6;
	color: #222;
	text-align: left;
	width: 100%;
}

/* Right Panel: Discussion & Input */
.right-panel {
	flex: 1.2;
	display: flex;
	flex-direction: column;
	gap: 15px;
	overflow-y: auto;
	padding-right: 5px; /* For scrollbar space */
}

.student-response {
	background: white; /* Only if you want cards, but screenshot shows clean background for text */
	display: flex;
	gap: 20px;
	margin-bottom: 10px;
}

.student-info {
	display: flex;
	flex-direction: column;
	align-items: center;
	min-width: 80px;
}

.student-text {
	font-size: 16px;
	line-height: 1.6;
	background-color: white; /* Or transparent */
	color: #333;
	margin-top: 5px;
}

/* Writing Area */
.writing-area {
	background: white;
	border: 1px solid #ccc;
	border-radius: var(--border-radius);
	display: flex;
	flex-direction: column;
	flex: 1;
	min-height: 300px;
}

.toolbar {
	background-color: #f9f9f9;
	padding: 10px 15px;
	border-bottom: 1px solid #e0e0e0;
	border-radius: var(--border-radius) var(--border-radius) 0 0;
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.tools-left {
	display: flex;
	gap: 5px;
}

.tool-btn {
	border: none;
	padding: 6px 15px;
	border-radius: 4px;
	font-size: 13px;
	cursor: pointer;
	font-weight: bold;
}

.tool-btn.primary {
	background-color: #2b7b78; /* Active state color in screenshot */
	color: white;
}

.tool-btn.secondary {
	background-color: var(--btn-grey);
	color: #555;
}

.word-count-controls {
	display: flex;
	align-items: center;
	gap: 10px;
	font-size: 14px;
	color: var(--primary-color);
	font-weight: bold;
}

textarea {
	flex: 1;
	border: none;
	padding: 20px;
	font-size: 16px;
	font-family: Arial, sans-serif;
	resize: none;
	outline: none;
	border-radius: 0 0 var(--border-radius) var(--border-radius);
}
</style>
