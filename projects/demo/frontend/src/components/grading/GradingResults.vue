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
			<!-- 结构化评分区域 -->
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

				<div class="evaluation-content">
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
							<div v-else class="text-content placeholder">正在生成总评...</div>
						</div>
					</div>
				</div>
			</div>

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
import type { ParsedComment } from "../../api/service";

const router = useRouter();

defineProps<{
	answer: string;
	polishedAnswer: string;
	parsedComment: ParsedComment;
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

/* 结构化评分区域 */
.evaluation-section {
	border: 1px solid rgba(0, 0, 0, 0.08);
	border-radius: 10px;
	background: rgba(255, 255, 255, 0.9);
	backdrop-filter: blur(10px);
	overflow: hidden;
	box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
	transition: all 0.3s ease;
	margin-bottom: 2rem;
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
	color: rgba(255, 255, 255, 0.9);
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

@media (max-width: 768px) {
	.comparison-section {
		grid-template-columns: 1fr;
	}

	.evaluation-header {
		flex-direction: column;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.score-display {
		align-self: flex-end;
	}
}
</style>
