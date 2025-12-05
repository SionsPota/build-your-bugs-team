<template>
	<div class="grading-results">
		<!-- 空状态提示 -->
		<div v-if="isEmpty" class="empty-state">
			<div class="empty-icon">📭</div>
			<h2 class="empty-title">未找到历史记录</h2>
			<p class="empty-message">
				该历史记录不存在或已被删除，请返回主面板查看其他记录。
			</p>
			<div class="empty-actions">
				<button @click="handleGoHome" class="btn btn-primary">
					返回主面板
				</button>
			</div>
		</div>

		<!-- 正常内容 -->
		<template v-else>
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

			<div class="comment-section">
				<div class="comment-header">
					<h3>评分评语</h3>
					<span
						v-if="currentStage === 'evaluating' && !comment"
						class="loading-indicator"
					>
						生成中...
					</span>
				</div>
				<div class="comment-content">
					<div class="text-content">{{ comment || "正在生成评语..." }}</div>
				</div>
			</div>

			<!-- 错误提示 -->
			<div v-if="error" class="error-message">
				{{ error }}
			</div>

			<div class="results-actions">
				<button @click="$emit('clear')" class="btn">重新开始</button>
				<button @click="handleGoHome" class="btn btn-secondary">
					返回主面板
				</button>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

defineProps<{
	answer: string;
	comment: string;
	polishedAnswer: string;
	currentStage: "idle" | "evaluating" | "polishing" | "done";
	loading?: boolean;
	error?: string | null;
	isEmpty?: boolean;
}>();

const emit = defineEmits<{
	(e: "clear"): void;
}>();

const handleGoHome = () => {
	router.push("/home");
};
</script>

<style scoped>
.grading-results {
	flex: 1;
	display: flex;
	flex-direction: column;
	padding: 2rem;
	overflow-y: auto;
}

.comparison-section {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 1rem;
	margin-bottom: 1rem;
}

.comparison-panel {
	border: 1px solid #ddd;
	border-radius: 4px;
	display: flex;
	flex-direction: column;
}

.panel-header {
	padding: 1rem;
	border-bottom: 1px solid #ddd;
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.panel-header h3 {
	margin: 0;
	font-size: 1rem;
}

.panel-content {
	flex: 1;
	padding: 1rem;
	overflow-y: auto;
}

.text-content {
	white-space: pre-wrap;
	word-wrap: break-word;
	line-height: 1.6;
}

.loading-indicator {
	color: #666;
	font-size: 0.9rem;
}

.comment-section {
	border: 1px solid #ddd;
	border-radius: 4px;
	margin-bottom: 1rem;
}

.comment-header {
	padding: 1rem;
	border-bottom: 1px solid #ddd;
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.comment-header h3 {
	margin: 0;
	font-size: 1rem;
}

.comment-content {
	padding: 1rem;
}

.results-actions {
	display: flex;
	justify-content: center;
	gap: 1rem;
}

.btn {
	padding: 0.75rem 1.5rem;
	border: 1px solid #ddd;
	background: #fff;
	cursor: pointer;
	border-radius: 4px;
	transition: all 0.2s;
}

.btn:hover {
	background: #f5f5f5;
}

.btn-primary {
	background: #667eea;
	color: white;
	border-color: #667eea;
}

.btn-primary:hover {
	background: #5568d3;
	border-color: #5568d3;
}

.btn-secondary {
	background: #f5f5f5;
	color: #333;
}

.btn-secondary:hover {
	background: #e0e0e0;
}

.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 4rem 2rem;
	text-align: center;
	min-height: 400px;
}

.empty-icon {
	font-size: 4rem;
	margin-bottom: 1rem;
	opacity: 0.6;
}

.empty-title {
	margin: 0 0 1rem 0;
	font-size: 1.5rem;
	color: #333;
	font-weight: 600;
}

.empty-message {
	margin: 0 0 2rem 0;
	color: #666;
	font-size: 1rem;
	line-height: 1.6;
	max-width: 400px;
}

.empty-actions {
	display: flex;
	gap: 1rem;
}

.error-message {
	margin: 1rem 0;
	padding: 0.75rem;
	background: #ffebee;
	color: #c62828;
	border-radius: 4px;
	border: 1px solid #ef5350;
}

@media (max-width: 768px) {
	.comparison-section {
		grid-template-columns: 1fr;
	}
}
</style>
