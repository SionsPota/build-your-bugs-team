<script setup lang="ts">
import { computed } from "vue";
import type { History } from "../api/history";

const props = defineProps<{
	show: boolean;
	history: History | null;
}>();

const emit = defineEmits<{
	close: [];
	delete: [historyId: number];
}>();

const formatDate = (dateString: string) => {
	const date = new Date(dateString);
	return date.toLocaleString("zh-CN", {
		year: "numeric",
		month: "2-digit",
		day: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
	});
};

const handleClose = () => {
	emit("close");
};

const handleDelete = () => {
	if (props.history) {
		if (confirm("确定要删除这条历史记录吗？")) {
			emit("delete", props.history.id);
		}
	}
};

const canShow = computed(() => props.show && props.history !== null);
</script>

<template>
	<Teleport to="body">
		<div v-if="canShow" class="history-detail-overlay" @click="handleClose">
			<div class="overlay-content" @click.stop>
				<div class="overlay-header">
					<h2>历史记录详情</h2>
					<button class="close-btn" @click="handleClose" aria-label="关闭">
						<svg
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<line x1="18" y1="6" x2="6" y2="18"></line>
							<line x1="6" y1="6" x2="18" y2="18"></line>
						</svg>
					</button>
				</div>

				<div class="overlay-body">
					<div class="detail-section">
						<div class="detail-label">创建时间</div>
						<div class="detail-value">
							{{ formatDate(history!.created_at) }}
						</div>
					</div>

					<div class="detail-section">
						<div class="detail-label">题名</div>
						<div class="detail-value">{{ history!.question }}</div>
					</div>

					<div class="detail-section">
						<div class="detail-label">原文</div>
						<div class="detail-text">{{ history!.answer }}</div>
					</div>

					<div v-if="history!.comment" class="detail-section">
						<div class="detail-label">评语</div>
						<div class="detail-text">{{ history!.comment }}</div>
					</div>

					<div v-if="history!.polished_answer" class="detail-section">
						<div class="detail-label">润色后</div>
						<div class="detail-text">{{ history!.polished_answer }}</div>
					</div>
				</div>

				<div class="overlay-footer">
					<button class="btn-secondary" @click="handleClose">关闭</button>
					<button class="btn-danger" @click="handleDelete">删除</button>
				</div>
			</div>
		</div>
	</Teleport>
</template>

<style scoped>
.history-detail-overlay {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background: rgba(0, 0, 0, 0.6);
	backdrop-filter: blur(8px);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 2000;
	animation: fadeIn 0.3s ease;
	padding: 1rem;
	overflow-y: auto;
}

@keyframes fadeIn {
	from {
		opacity: 0;
	}
	to {
		opacity: 1;
	}
}

.overlay-content {
	background: white;
	border-radius: 16px;
	width: 100%;
	max-width: 900px;
	max-height: 90vh;
	display: flex;
	flex-direction: column;
	box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
	animation: slideUp 0.3s ease;
	overflow: hidden;
}

@keyframes slideUp {
	from {
		transform: translateY(30px);
		opacity: 0;
	}
	to {
		transform: translateY(0);
		opacity: 1;
	}
}

.overlay-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 1.5rem 2rem;
	border-bottom: 1px solid #e0e0e0;
	background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	color: white;
	flex-shrink: 0;
}

.overlay-header h2 {
	margin: 0;
	font-size: 1.5rem;
	font-weight: 700;
}

.close-btn {
	background: rgba(255, 255, 255, 0.2);
	border: none;
	color: white;
	width: 40px;
	height: 40px;
	border-radius: 50%;
	cursor: pointer;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: all 0.2s;
	padding: 0;
}

.close-btn:hover {
	background: rgba(255, 255, 255, 0.3);
	transform: rotate(90deg);
}

.close-btn:active {
	transform: rotate(90deg) scale(0.95);
}

.overlay-body {
	flex: 1;
	overflow-y: auto;
	padding: 2rem;
	scrollbar-width: thin;
	scrollbar-color: #cbd5e0 #f7fafc;
}

.overlay-body::-webkit-scrollbar {
	width: 8px;
}

.overlay-body::-webkit-scrollbar-track {
	background: #f7fafc;
	border-radius: 4px;
}

.overlay-body::-webkit-scrollbar-thumb {
	background: #cbd5e0;
	border-radius: 4px;
}

.overlay-body::-webkit-scrollbar-thumb:hover {
	background: #a0aec0;
}

.detail-section {
	margin-bottom: 2rem;
}

.detail-section:last-child {
	margin-bottom: 0;
}

.detail-label {
	font-weight: 600;
	color: #333;
	margin-bottom: 0.75rem;
	font-size: 0.95rem;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: #667eea;
}

.detail-value {
	color: #666;
	font-size: 1rem;
	padding: 0.75rem 1rem;
	background: #f8f9fa;
	border-radius: 8px;
	border-left: 4px solid #667eea;
}

.detail-text {
	color: #333;
	line-height: 1.8;
	white-space: pre-wrap;
	word-wrap: break-word;
	padding: 1.25rem;
	background: #f8f9fa;
	border-radius: 8px;
	border: 1px solid #e0e0e0;
	font-size: 0.95rem;
	max-height: 400px;
	overflow-y: auto;
	scrollbar-width: thin;
	scrollbar-color: #cbd5e0 #f7fafc;
}

.detail-text::-webkit-scrollbar {
	width: 6px;
}

.detail-text::-webkit-scrollbar-track {
	background: #f7fafc;
	border-radius: 3px;
}

.detail-text::-webkit-scrollbar-thumb {
	background: #cbd5e0;
	border-radius: 3px;
}

.detail-text::-webkit-scrollbar-thumb:hover {
	background: #a0aec0;
}

.overlay-footer {
	display: flex;
	justify-content: flex-end;
	gap: 1rem;
	padding: 1.5rem 2rem;
	border-top: 1px solid #e0e0e0;
	background: #f8f9fa;
	flex-shrink: 0;
}

.btn-secondary,
.btn-danger {
	padding: 0.75rem 1.5rem;
	border: none;
	border-radius: 8px;
	font-size: 0.95rem;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.3s;
}

.btn-secondary {
	background: #f5f5f5;
	color: #333;
	border: 1px solid #e0e0e0;
}

.btn-secondary:hover {
	background: #eeeeee;
	border-color: #b0bec5;
	transform: translateY(-1px);
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.btn-danger {
	background: #ff5252;
	color: white;
}

.btn-danger:hover {
	background: #ff1744;
	transform: translateY(-1px);
	box-shadow: 0 2px 12px rgba(255, 82, 82, 0.4);
}

.btn-secondary:active,
.btn-danger:active {
	transform: translateY(0);
}

/* 响应式设计 */
@media (max-width: 768px) {
	.history-detail-overlay {
		padding: 0.5rem;
	}

	.overlay-content {
		max-height: 95vh;
		border-radius: 12px;
	}

	.overlay-header {
		padding: 1rem 1.5rem;
	}

	.overlay-header h2 {
		font-size: 1.25rem;
	}

	.overlay-body {
		padding: 1.5rem;
	}

	.overlay-footer {
		padding: 1rem 1.5rem;
		flex-direction: column;
	}

	.btn-secondary,
	.btn-danger {
		width: 100%;
	}
}
</style>
