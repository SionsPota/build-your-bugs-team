<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from "vue";
import {
	gradeAndPolishStream,
	healthCheck,
	downloadTelemetryLog,
	type StreamEvent,
	type ParsedComment,
} from "./api/service";

// 响应式数据
const answer = ref("");
const questionFile = ref("test.yaml");
const loading = ref(false);
const error = ref<string | null>(null);
const comment = ref("");
const polishedAnswer = ref("");
const isBackendHealthy = ref<boolean | null>(null);
const statusMessage = ref<string | null>(null);
const currentStage = ref<"idle" | "evaluating" | "polishing" | "done">("idle");
const downloadingLog = ref(false);

// 结构化评语数据
const parsedComment = ref<ParsedComment>({
	strengths: [],
	weaknesses: [],
	opportunities: [],
	overview: "",
	score: null,
	raw_text: "",
});

// 引用评分内容区域和结果视图，用于自动滚动
const evaluationContentRef = ref<HTMLElement | null>(null);
const resultsViewRef = ref<HTMLElement | null>(null);

// 自动滚动到底部的函数
const scrollToBottom = () => {
	nextTick(() => {
		// 使用 setTimeout 确保 DOM 完全更新
		setTimeout(() => {
			// 先滚动 evaluation-content 区域到底部
			if (evaluationContentRef.value) {
				evaluationContentRef.value.scrollTo({
					top: evaluationContentRef.value.scrollHeight,
					behavior: "smooth",
				});
			}
			// 然后滚动整个 results-view 到底部
			if (resultsViewRef.value) {
				resultsViewRef.value.scrollTo({
					top: resultsViewRef.value.scrollHeight,
					behavior: "smooth",
				});
			}
			// 最后滚动整个页面到评分区域
			setTimeout(() => {
				if (evaluationContentRef.value) {
					evaluationContentRef.value.scrollIntoView({
						behavior: "smooth",
						block: "end",
					});
				}
			}, 200);
		}, 50);
	});
};

// 监听结构化评语数据的变化，自动滚动
watch(
	() => [
		parsedComment.value.strengths.length,
		parsedComment.value.weaknesses.length,
		parsedComment.value.opportunities.length,
		parsedComment.value.overview,
		parsedComment.value.score,
	],
	() => {
		if (currentStage.value === "evaluating") {
			scrollToBottom();
		}
	},
	{ deep: true }
);

// 计算属性：是否有结果
const hasResults = computed(
	() =>
		comment.value ||
		polishedAnswer.value ||
		parsedComment.value.score !== null ||
		parsedComment.value.strengths.length > 0 ||
		parsedComment.value.weaknesses.length > 0 ||
		parsedComment.value.opportunities.length > 0 ||
		parsedComment.value.overview.length > 0
);

// 检查后端健康状态
const checkBackend = async () => {
	try {
		await healthCheck();
		isBackendHealthy.value = true;
	} catch (err) {
		isBackendHealthy.value = false;
		console.error("Backend health check failed:", err);
	}
};

// 提交评分和润色请求（流式）
const handleSubmit = async () => {
	if (!answer.value.trim()) {
		error.value = "请输入学生作文内容";
		return;
	}

	loading.value = true;
	error.value = null;
	comment.value = "";
	polishedAnswer.value = "";
	statusMessage.value = null;
	currentStage.value = "idle";
	// 重置结构化评语数据
	parsedComment.value = {
		strengths: [],
		weaknesses: [],
		opportunities: [],
		overview: "",
		score: null,
		raw_text: "",
	};

	try {
		await gradeAndPolishStream(
			answer.value,
			questionFile.value,
			(event: StreamEvent) => {
				switch (event.type) {
					case "status":
						statusMessage.value = event.message || "";
						if (event.stage === "evaluating") {
							currentStage.value = "evaluating";
						} else if (event.stage === "polishing") {
							currentStage.value = "polishing";
						}
						break;

					case "comment_chunk":
						if (event.content) {
							comment.value += event.content;
						}
						break;

					case "comment_parsed":
						// 实时更新结构化数据
						if (event.data) {
							if (event.data.strengths !== undefined) {
								parsedComment.value.strengths = event.data.strengths;
							}
							if (event.data.weaknesses !== undefined) {
								parsedComment.value.weaknesses = event.data.weaknesses;
							}
							if (event.data.opportunities !== undefined) {
								parsedComment.value.opportunities = event.data.opportunities;
							}
							if (event.data.overview !== undefined) {
								parsedComment.value.overview = event.data.overview;
							}
							if (event.data.score !== undefined) {
								parsedComment.value.score = event.data.score;
							}
						}
						break;

					case "comment_complete":
						if (event.comment) {
							comment.value = event.comment;
						}
						// 更新完整的结构化数据
						if (event.parsed_comment) {
							parsedComment.value = event.parsed_comment;
						}
						currentStage.value = "polishing";
						// 确保滚动到底部显示完整内容
						scrollToBottom();
						break;

					case "polished_chunk":
						if (event.content) {
							polishedAnswer.value += event.content;
						}
						break;

					case "polished_complete":
						if (event.polished_answer) {
							polishedAnswer.value = event.polished_answer;
						}
						break;

					case "done":
						currentStage.value = "done";
						statusMessage.value = "处理完成";
						loading.value = false;
						break;

					case "error":
						error.value = event.message || "处理过程中发生错误";
						loading.value = false;
						currentStage.value = "idle";
						break;
				}
			}
		);
	} catch (err) {
		error.value =
			err instanceof Error ? err.message : "请求失败，请检查后端服务是否运行";
		console.error("Error:", err);
		loading.value = false;
		currentStage.value = "idle";
	}
};

// 清空所有内容
const handleClear = () => {
	answer.value = "";
	comment.value = "";
	polishedAnswer.value = "";
	error.value = null;
	statusMessage.value = null;
	currentStage.value = "idle";
	parsedComment.value = {
		strengths: [],
		weaknesses: [],
		opportunities: [],
		overview: "",
		score: null,
		raw_text: "",
	};
};

// 下载遥测日志
const handleDownloadLog = async () => {
	downloadingLog.value = true;
	try {
		const blob = await downloadTelemetryLog();
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = "telemetry.log";
		a.click();
		URL.revokeObjectURL(url);
	} catch (err) {
		error.value =
			err instanceof Error ? err.message : "下载日志失败，请检查后端日志接口";
		console.error("Download log error:", err);
	} finally {
		downloadingLog.value = false;
	}
};

// 组件挂载时检查后端
onMounted(() => {
	checkBackend();
});
</script>

<template>
	<div class="app-container">
		<!-- 侧边栏 -->
		<aside class="sidebar">
			<div class="sidebar-header">
				<h2>TOEFL 写作评分</h2>
			</div>
			<div class="sidebar-content">
				<div class="status-item">
					<span class="status-label">后端状态</span>
					<span
						class="status-value"
						:class="{
							healthy: isBackendHealthy,
							unhealthy: isBackendHealthy === false,
						}"
					>
						<span v-if="isBackendHealthy === null">检查中</span>
						<span v-else-if="isBackendHealthy">正常</span>
						<span v-else>未连接</span>
					</span>
				</div>

				<div class="status-item">
					<span class="status-label">题目文件</span>
					<input
						v-model="questionFile"
						type="text"
						class="status-input"
						placeholder="test.yaml"
					/>
				</div>

				<div v-if="loading" class="status-item">
					<span class="status-label">处理状态</span>
					<span class="status-value processing">
						{{ statusMessage || "处理中..." }}
					</span>
				</div>

				<div class="sidebar-actions">
					<button @click="checkBackend" class="btn-sidebar">检查连接</button>
					<button
						@click="handleDownloadLog"
						class="btn-sidebar"
						:disabled="downloadingLog"
					>
						<span v-if="downloadingLog">下载中...</span>
						<span v-else>下载遥测日志</span>
					</button>
				</div>
			</div>
		</aside>

		<!-- 主内容区 -->
		<main class="main-content" :class="{ 'has-results': hasResults }">
			<!-- 初始状态：输入界面 -->
			<div v-if="!hasResults" class="input-view">
				<div class="input-container">
					<label for="answer" class="input-label">学生作文</label>
					<textarea
						id="answer"
						v-model="answer"
						placeholder="请输入学生的作文内容..."
						class="textarea-main"
						rows="15"
					></textarea>

					<div class="input-actions">
						<button
							@click="handleSubmit"
							:disabled="loading || !answer.trim()"
							class="btn-primary"
						>
							<span v-if="loading">处理中...</span>
							<span v-else>提交</span>
						</button>
						<button
							@click="handleClear"
							class="btn-secondary"
							:disabled="loading"
						>
							清空
						</button>
					</div>

					<div v-if="error" class="error-message">
						{{ error }}
					</div>
				</div>
			</div>

			<!-- 结果状态：对比视图 -->
			<div v-else class="results-view" ref="resultsViewRef">
				<!-- 上方：结构化评分 -->
				<div class="evaluation-section">
					<div class="evaluation-header">
						<h3>评分结果</h3>
						<div class="score-display" v-if="parsedComment.score !== null">
							<span class="score-label">分数：</span>
							<span class="score-value">{{ parsedComment.score }}</span>
						</div>
						<span
							v-else-if="currentStage === 'evaluating'"
							class="loading-indicator"
						>
							生成中...
						</span>
					</div>

					<div class="evaluation-content" ref="evaluationContentRef">
						<!-- 优点 -->
						<div
							class="evaluation-category"
							v-if="
								parsedComment.strengths.length > 0 ||
								currentStage === 'evaluating'
							"
						>
							<div class="category-header strengths-header">
								<h4>优点</h4>
							</div>
							<ul class="category-list">
								<li
									v-for="(item, index) in parsedComment.strengths"
									:key="index"
									class="category-item strengths-item"
								>
									{{ item }}
								</li>
								<li
									v-if="
										parsedComment.strengths.length === 0 &&
										currentStage === 'evaluating'
									"
									class="category-item placeholder"
								>
									正在分析...
								</li>
							</ul>
						</div>

						<!-- 缺点 -->
						<div
							class="evaluation-category"
							v-if="
								parsedComment.weaknesses.length > 0 ||
								currentStage === 'evaluating'
							"
						>
							<div class="category-header weaknesses-header">
								<h4>缺点</h4>
							</div>
							<ul class="category-list">
								<li
									v-for="(item, index) in parsedComment.weaknesses"
									:key="index"
									class="category-item weaknesses-item"
								>
									{{ item }}
								</li>
								<li
									v-if="
										parsedComment.weaknesses.length === 0 &&
										currentStage === 'evaluating'
									"
									class="category-item placeholder"
								>
									正在分析...
								</li>
							</ul>
						</div>

						<!-- 待提升 -->
						<div
							class="evaluation-category"
							v-if="
								parsedComment.opportunities.length > 0 ||
								currentStage === 'evaluating'
							"
						>
							<div class="category-header opportunities-header">
								<h4>待提升</h4>
							</div>
							<ul class="category-list">
								<li
									v-for="(item, index) in parsedComment.opportunities"
									:key="index"
									class="category-item opportunities-item"
								>
									{{ item }}
								</li>
								<li
									v-if="
										parsedComment.opportunities.length === 0 &&
										currentStage === 'evaluating'
									"
									class="category-item placeholder"
								>
									正在分析...
								</li>
							</ul>
						</div>

						<!-- 总评 -->
						<div
							class="evaluation-category overview-category"
							v-if="parsedComment.overview || currentStage === 'evaluating'"
						>
							<div class="category-header overview-header">
								<h4>总评</h4>
							</div>
							<div class="overview-content">
								<div v-if="parsedComment.overview" class="text-content">
									{{ parsedComment.overview }}
								</div>
								<div v-else class="text-content placeholder">
									正在生成总评...
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- 下方：原文和润色对比 -->
				<div class="comparison-section">
					<div class="comparison-panel">
						<div class="panel-header">
							<h3>原文</h3>
						</div>
						<div class="panel-content">
							<div class="text-content">{{ answer }}</div>
						</div>
					</div>

					<div class="comparison-panel">
						<div class="panel-header">
							<h3>润色后</h3>
							<span
								v-if="currentStage === 'polishing' && !polishedAnswer"
								class="loading-indicator"
							>
								生成中...
							</span>
						</div>
						<div class="panel-content">
							<div class="text-content">
								{{ polishedAnswer || "正在生成..." }}
							</div>
						</div>
					</div>
				</div>

				<!-- 操作按钮 -->
				<div class="results-actions">
					<button @click="handleClear" class="btn-secondary">重新开始</button>
				</div>
			</div>
		</main>
	</div>
</template>

<style scoped>
* {
	box-sizing: border-box;
}

.app-container {
	display: flex;
	min-height: 100vh;
	background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
		"Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
	-webkit-font-smoothing: antialiased;
	-moz-osx-font-smoothing: grayscale;
	text-rendering: optimizeLegibility;
}

/* 侧边栏 */
.sidebar {
	width: 240px;
	background: rgba(255, 255, 255, 0.95);
	backdrop-filter: blur(10px);
	border-right: 1px solid rgba(0, 0, 0, 0.08);
	display: flex;
	flex-direction: column;
	flex-shrink: 0;
	box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
}

.sidebar-header {
	padding: 1.5rem 1rem;
	border-bottom: 1px solid rgba(0, 0, 0, 0.08);
	background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	color: white;
}

.sidebar-header h2 {
	margin: 0;
	font-size: 1.15rem;
	font-weight: 700;
	color: white;
	letter-spacing: 0.8px;
	text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.sidebar-content {
	padding: 1rem;
	flex: 1;
}

.status-item {
	margin-bottom: 1.5rem;
	animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
	from {
		opacity: 0;
		transform: translateY(-5px);
	}
	to {
		opacity: 1;
		transform: translateY(0);
	}
}

.status-label {
	display: block;
	font-size: 0.875rem;
	color: #555;
	margin-bottom: 0.5rem;
	font-weight: 600;
	letter-spacing: 0.2px;
	text-transform: uppercase;
	font-size: 0.75rem;
}

.status-value {
	display: block;
	font-size: 0.95rem;
	color: #333;
	padding: 0.6rem 0.75rem;
	background: #f8f9fa;
	border-radius: 6px;
	transition: all 0.3s ease;
	border: 1px solid transparent;
	font-weight: 500;
	letter-spacing: 0.3px;
}

.status-value.healthy {
	color: #2e7d32;
	background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
	border-color: #81c784;
	box-shadow: 0 2px 4px rgba(46, 125, 50, 0.1);
}

.status-value.unhealthy {
	color: #c62828;
	background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
	border-color: #e57373;
	box-shadow: 0 2px 4px rgba(198, 40, 40, 0.1);
}

.status-value.processing {
	color: #1976d2;
	background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
	border-color: #64b5f6;
	box-shadow: 0 2px 4px rgba(25, 118, 210, 0.1);
	animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
	0%,
	100% {
		opacity: 1;
	}
	50% {
		opacity: 0.8;
	}
}

.status-input {
	width: 100%;
	padding: 0.6rem 0.75rem;
	border: 1px solid #e0e0e0;
	border-radius: 6px;
	font-size: 0.9rem;
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
		"Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
	transition: all 0.3s ease;
	background: #ffffff;
	font-weight: 400;
	letter-spacing: 0.2px;
	color: #2d3748;
}

.status-input:focus {
	outline: none;
	border-color: #667eea;
	box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
	transform: translateY(-1px);
}

.sidebar-actions {
	margin-top: 2rem;
}

.btn-sidebar {
	width: 100%;
	padding: 0.7rem;
	background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
	border: 1px solid #e0e0e0;
	border-radius: 6px;
	font-size: 0.875rem;
	cursor: pointer;
	transition: all 0.3s ease;
	font-weight: 600;
	color: #555;
	letter-spacing: 0.3px;
}

.btn-sidebar:hover {
	background: linear-gradient(135deg, #eeeeee 0%, #e0e0e0 100%);
	transform: translateY(-2px);
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.btn-sidebar:active {
	transform: translateY(0);
}

/* 主内容区 */
.main-content {
	flex: 1;
	display: flex;
	flex-direction: column;
	overflow: hidden;
	transition: background 0.3s ease;
}

.main-content.has-results {
	background: rgba(255, 255, 255, 0.95);
	backdrop-filter: blur(10px);
}

/* 输入视图 */
.input-view {
	flex: 1;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 3rem 2rem;
	animation: fadeInUp 0.5s ease-out;
}

@keyframes fadeInUp {
	from {
		opacity: 0;
		transform: translateY(20px);
	}
	to {
		opacity: 1;
		transform: translateY(0);
	}
}

.input-container {
	width: 100%;
	max-width: 800px;
	background: rgba(255, 255, 255, 0.9);
	backdrop-filter: blur(10px);
	padding: 2.5rem;
	border-radius: 12px;
	box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
	border: 1px solid rgba(255, 255, 255, 0.2);
}

.input-label {
	display: block;
	font-size: 1.125rem;
	font-weight: 700;
	color: #2d3748;
	margin-bottom: 1rem;
	letter-spacing: 0.5px;
	text-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.textarea-main {
	width: 100%;
	padding: 1.25rem;
	border: 2px solid #e0e0e0;
	border-radius: 8px;
	font-size: 1rem;
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
		"Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
	line-height: 1.75;
	resize: vertical;
	background: #ffffff;
	transition: all 0.3s ease;
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	color: #2d3748;
	font-weight: 400;
	letter-spacing: 0.2px;
}

.textarea-main:hover {
	border-color: #b0bec5;
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

.textarea-main:focus {
	outline: none;
	border-color: #667eea;
	box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1), 0 4px 12px rgba(0, 0, 0, 0.1);
	transform: translateY(-2px);
}

.input-actions {
	display: flex;
	gap: 0.75rem;
	margin-top: 1.5rem;
}

.btn-primary,
.btn-secondary {
	padding: 0.875rem 2rem;
	border: none;
	border-radius: 8px;
	font-size: 1rem;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.3s ease;
	position: relative;
	overflow: hidden;
	letter-spacing: 0.5px;
	text-transform: uppercase;
	font-size: 0.875rem;
	text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.btn-primary {
	background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	color: white;
	box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.btn-primary::before {
	content: "";
	position: absolute;
	top: 50%;
	left: 50%;
	width: 0;
	height: 0;
	border-radius: 50%;
	background: rgba(255, 255, 255, 0.3);
	transform: translate(-50%, -50%);
	transition: width 0.6s, height 0.6s;
}

.btn-primary:hover:not(:disabled) {
	transform: translateY(-2px);
	box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.btn-primary:hover:not(:disabled)::before {
	width: 300px;
	height: 300px;
}

.btn-primary:active:not(:disabled) {
	transform: translateY(0);
}

.btn-primary:disabled {
	opacity: 0.6;
	cursor: not-allowed;
	transform: none;
}

.btn-secondary {
	background: linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%);
	color: #555;
	border: 2px solid #e0e0e0;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.btn-secondary:hover:not(:disabled) {
	background: linear-gradient(135deg, #f8f8f8 0%, #eeeeee 100%);
	border-color: #b0bec5;
	transform: translateY(-2px);
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.btn-secondary:active:not(:disabled) {
	transform: translateY(0);
}

.btn-secondary:disabled {
	opacity: 0.6;
	cursor: not-allowed;
	transform: none;
}

.error-message {
	margin-top: 1rem;
	padding: 1rem 1.25rem;
	background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
	color: #c62828;
	border-radius: 8px;
	border-left: 4px solid #c62828;
	font-size: 0.9rem;
	animation: shake 0.5s ease-in-out;
	box-shadow: 0 2px 8px rgba(198, 40, 40, 0.2);
	font-weight: 500;
	letter-spacing: 0.2px;
	line-height: 1.6;
}

@keyframes shake {
	0%,
	100% {
		transform: translateX(0);
	}
	25% {
		transform: translateX(-5px);
	}
	75% {
		transform: translateX(5px);
	}
}

/* 结果视图 */
.results-view {
	flex: 1;
	display: flex;
	flex-direction: column;
	padding: 2rem;
	gap: 2rem;
	overflow: auto;
	animation: fadeIn 0.5s ease-out;
}

.comparison-section {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 2rem;
	min-height: 400px;
}

.comparison-panel {
	display: flex;
	flex-direction: column;
	border: 1px solid rgba(0, 0, 0, 0.08);
	border-radius: 10px;
	background: rgba(255, 255, 255, 0.9);
	backdrop-filter: blur(10px);
	overflow: hidden;
	box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
	transition: all 0.3s ease;
}

.comparison-panel:hover {
	transform: translateY(-4px);
	box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
}

.panel-header {
	padding: 1.25rem 1.5rem;
	background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
	border-bottom: 1px solid rgba(0, 0, 0, 0.08);
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.panel-header h3 {
	margin: 0;
	font-size: 1.1rem;
	font-weight: 700;
	color: #2d3748;
	letter-spacing: 0.5px;
	text-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.panel-content {
	flex: 1;
	padding: 1.5rem;
	overflow: auto;
	scrollbar-width: thin;
	scrollbar-color: #cbd5e0 #f7fafc;
}

.panel-content::-webkit-scrollbar {
	width: 8px;
}

.panel-content::-webkit-scrollbar-track {
	background: #f7fafc;
	border-radius: 4px;
}

.panel-content::-webkit-scrollbar-thumb {
	background: #cbd5e0;
	border-radius: 4px;
}

.panel-content::-webkit-scrollbar-thumb:hover {
	background: #a0aec0;
}

/* 结构化评分区域 */
.evaluation-section {
	border: 1px solid rgba(0, 0, 0, 0.08);
	border-radius: 10px;
	background: rgba(255, 255, 255, 0.9);
	backdrop-filter: blur(10px);
	overflow: hidden;
	box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
	transition: all 0.3s ease;
}

.evaluation-section:hover {
	box-shadow: 0 6px 25px rgba(0, 0, 0, 0.1);
}

.evaluation-header {
	padding: 1.25rem 1.5rem;
	background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	border-bottom: 1px solid rgba(0, 0, 0, 0.08);
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.evaluation-header h3 {
	margin: 0;
	font-size: 1.1rem;
	font-weight: 700;
	color: white;
	letter-spacing: 0.5px;
	text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.score-display {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.score-label {
	font-size: 0.9rem;
	color: rgba(255, 255, 255, 0.9);
	font-weight: 500;
}

.score-value {
	font-size: 1.5rem;
	font-weight: 700;
	color: white;
	background: rgba(255, 255, 255, 0.2);
	padding: 0.25rem 0.75rem;
	border-radius: 6px;
	text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.evaluation-content {
	padding: 1.5rem;
	display: flex;
	flex-direction: column;
	gap: 1.5rem;
	max-height: none;
	min-height: 200px;
	overflow-y: auto;
	overflow-x: hidden;
	scrollbar-width: thin;
	scrollbar-color: #cbd5e0 #f7fafc;
	scroll-behavior: smooth;
}

.evaluation-content::-webkit-scrollbar {
	width: 8px;
}

.evaluation-content::-webkit-scrollbar-track {
	background: #f7fafc;
	border-radius: 4px;
}

.evaluation-content::-webkit-scrollbar-thumb {
	background: #cbd5e0;
	border-radius: 4px;
}

.evaluation-content::-webkit-scrollbar-thumb:hover {
	background: #a0aec0;
}

.evaluation-category {
	border: 1px solid rgba(0, 0, 0, 0.06);
	border-radius: 8px;
	overflow: hidden;
	background: #fafafa;
	transition: all 0.3s ease;
}

.evaluation-category:hover {
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.category-header {
	padding: 0.875rem 1.25rem;
	border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.category-header h4 {
	margin: 0;
	font-size: 1rem;
	font-weight: 700;
	letter-spacing: 0.3px;
}

.strengths-header {
	background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
}

.strengths-header h4 {
	color: #2e7d32;
}

.weaknesses-header {
	background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
}

.weaknesses-header h4 {
	color: #c62828;
}

.opportunities-header {
	background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
}

.opportunities-header h4 {
	color: #1976d2;
}

.overview-header {
	background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
}

.overview-header h4 {
	color: #e65100;
}

.category-list {
	list-style: none;
	padding: 0;
	margin: 0;
}

.category-item {
	padding: 0.875rem 1.25rem;
	border-bottom: 1px solid rgba(0, 0, 0, 0.04);
	line-height: 1.6;
	color: #2d3748;
	font-size: 0.95rem;
	transition: all 0.2s ease;
	position: relative;
	padding-left: 2rem;
}

.category-item::before {
	content: "•";
	position: absolute;
	left: 1rem;
	font-weight: bold;
	font-size: 1.2rem;
}

.category-item:last-child {
	border-bottom: none;
}

.category-item:hover {
	background: rgba(255, 255, 255, 0.6);
}

.strengths-item {
	background: rgba(232, 245, 233, 0.3);
}

.strengths-item::before {
	color: #2e7d32;
}

.weaknesses-item {
	background: rgba(255, 235, 238, 0.3);
}

.weaknesses-item::before {
	color: #c62828;
}

.opportunities-item {
	background: rgba(227, 242, 253, 0.3);
}

.opportunities-item::before {
	color: #1976d2;
}

.category-item.placeholder {
	color: #999;
	font-style: italic;
	background: rgba(0, 0, 0, 0.02);
}

.category-item.placeholder::before {
	content: "…";
	color: #999;
}

.overview-category {
	background: rgba(255, 243, 224, 0.3);
}

.overview-content {
	padding: 1.25rem;
}

.overview-content .text-content {
	color: #2d3748;
	line-height: 1.85;
	white-space: pre-wrap;
	word-wrap: break-word;
	font-size: 0.95rem;
	animation: fadeInText 0.5s ease-out;
	font-weight: 400;
	letter-spacing: 0.15px;
	text-align: justify;
}

.overview-content .text-content.placeholder {
	color: #999;
	font-style: italic;
}

.text-content {
	color: #2d3748;
	line-height: 1.85;
	white-space: pre-wrap;
	word-wrap: break-word;
	font-size: 1rem;
	animation: fadeInText 0.5s ease-out;
	font-weight: 400;
	letter-spacing: 0.15px;
	text-align: justify;
	hyphens: auto;
	-webkit-hyphens: auto;
	-moz-hyphens: auto;
}

@keyframes fadeInText {
	from {
		opacity: 0;
	}
	to {
		opacity: 1;
	}
}

.loading-indicator {
	font-size: 0.875rem;
	color: #667eea;
	font-style: italic;
	display: inline-flex;
	align-items: center;
	gap: 0.5rem;
	font-weight: 500;
	letter-spacing: 0.3px;
}

.loading-indicator::after {
	content: "...";
	animation: dots 1.5s steps(4, end) infinite;
}

@keyframes dots {
	0%,
	20% {
		content: ".";
	}
	40% {
		content: "..";
	}
	60%,
	100% {
		content: "...";
	}
}

.results-actions {
	display: flex;
	justify-content: center;
	padding-top: 1.5rem;
	border-top: 1px solid rgba(0, 0, 0, 0.08);
}

/* 响应式设计 */
@media (max-width: 1024px) {
	.comparison-section {
		grid-template-columns: 1fr;
	}
}

@media (max-width: 768px) {
	.app-container {
		flex-direction: column;
	}

	.sidebar {
		width: 100%;
		border-right: none;
		border-bottom: 1px solid #e0e0e0;
	}

	.sidebar-content {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.status-item {
		flex: 1;
		min-width: 150px;
		margin-bottom: 0;
	}

	.input-view {
		padding: 2rem 1rem;
	}

	.results-view {
		padding: 1rem;
	}

	.evaluation-content {
		max-height: none;
	}

	.evaluation-header {
		flex-direction: column;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.score-display {
		align-self: flex-end;
	}

	.category-item {
		padding: 0.75rem 1rem;
		padding-left: 1.75rem;
		font-size: 0.9rem;
	}

	.overview-content {
		padding: 1rem;
	}
}
</style>
