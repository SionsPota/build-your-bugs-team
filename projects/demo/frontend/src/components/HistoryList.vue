<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { getHistories, deleteHistory, type History } from "../api/history";
import { useAuth } from "../composables/useAuth";

const router = useRouter();
const { isAuthenticated } = useAuth();

const histories = ref<History[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const currentPage = ref(1);
const totalPages = ref(1);
const total = ref(0);
const perPage = ref(10); // 在sidebar中显示更少的记录

const loadHistories = async (page: number = 1) => {
	if (!isAuthenticated.value) {
		histories.value = [];
		return;
	}

	loading.value = true;
	error.value = null;

	try {
		const response = await getHistories(page, perPage.value);
		histories.value = response.histories;
		currentPage.value = response.pagination.page;
		totalPages.value = response.pagination.pages;
		total.value = response.pagination.total;
	} catch (err) {
		error.value = err instanceof Error ? err.message : "加载历史记录失败";
		console.error("Load histories error:", err);
	} finally {
		loading.value = false;
	}
};

const handleDelete = async (historyId: number) => {
	if (!confirm("确定要删除这条历史记录吗？")) {
		return;
	}

	try {
		await deleteHistory(historyId);
		await loadHistories(currentPage.value);
	} catch (err) {
		error.value = err instanceof Error ? err.message : "删除失败";
		console.error("Delete history error:", err);
	}
};

const handleViewDetail = (history: History) => {
	router.push(`/history/${history.id}`);
};

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

const truncateText = (text: string, maxLength: number = 60) => {
	if (!text) return "";
	if (text.length <= maxLength) return text;
	return text.substring(0, maxLength) + "...";
};

// 监听认证状态变化
watch(isAuthenticated, (newVal) => {
	if (newVal) {
		loadHistories();
	} else {
		histories.value = [];
	}
});

onMounted(() => {
	if (isAuthenticated.value) {
		loadHistories();
	}
});

defineExpose({
	loadHistories,
});
</script>

<template>
	<div class="history-list-container">
		<div class="history-header">
			<h3>历史记录</h3>
			<button
				class="refresh-btn"
				@click="loadHistories(currentPage)"
				:disabled="loading"
				title="刷新"
			>
				{{ loading ? "..." : "↻" }}
			</button>
		</div>

		<div v-if="loading && histories.length === 0" class="loading-state">
			<p>加载中...</p>
		</div>

		<div v-else-if="error" class="error-state">
			<p>{{ error }}</p>
			<button class="retry-btn" @click="loadHistories(currentPage)">
				重试
			</button>
		</div>

		<div v-else-if="histories.length === 0" class="empty-state">
			<p>暂无历史记录</p>
		</div>

		<div v-else class="history-list">
			<div
				v-for="history in histories"
				:key="history.id"
				class="history-item"
				@click="handleViewDetail(history)"
			>
				<div class="history-header-item">
					<span class="history-date">{{ formatDate(history.created_at) }}</span>
					<span class="history-file">{{ history.question }}</span>
				</div>
				<div class="history-preview">
					<div class="preview-text">{{ truncateText(history.answer) }}</div>
				</div>
				<div class="history-actions">
					<button
						class="action-btn view-btn"
						@click.stop="handleViewDetail(history)"
					>
						查看
					</button>
					<button
						class="action-btn delete-btn"
						@click.stop="handleDelete(history.id)"
					>
						删除
					</button>
				</div>
			</div>

			<!-- 分页 -->
			<div v-if="totalPages > 1" class="pagination">
				<button
					class="page-btn"
					@click="loadHistories(currentPage - 1)"
					:disabled="currentPage === 1 || loading"
				>
					‹
				</button>
				<span class="page-info"> {{ currentPage }}/{{ totalPages }} </span>
				<button
					class="page-btn"
					@click="loadHistories(currentPage + 1)"
					:disabled="currentPage === totalPages || loading"
				>
					›
				</button>
			</div>
		</div>
	</div>
</template>

<style scoped>
.history-list-container {
	display: flex;
	flex-direction: column;
}

.history-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 0.75rem;
}

.history-header h3 {
	margin: 0;
	font-size: 0.9rem;
	font-weight: 700;
	color: #2d3748;
}

.refresh-btn {
	padding: 0.25rem 0.5rem;
	background: #667eea;
	color: white;
	border: none;
	border-radius: 4px;
	font-size: 0.75rem;
	cursor: pointer;
	transition: all 0.2s;
	min-width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.refresh-btn:hover:not(:disabled) {
	background: #5568d3;
}

.refresh-btn:disabled {
	opacity: 0.6;
	cursor: not-allowed;
}

.empty-state,
.loading-state,
.error-state {
	padding: 1rem;
	text-align: center;
	color: #666;
	font-size: 0.875rem;
}

.error-state {
	color: #c62828;
}

.retry-btn {
	margin-top: 0.5rem;
	padding: 0.375rem 0.75rem;
	background: #667eea;
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	font-size: 0.875rem;
}

.history-list {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
}

.history-item {
	padding: 0.75rem;
	background: #f8f9fa;
	border: 1px solid #e0e0e0;
	border-radius: 6px;
	cursor: pointer;
	transition: all 0.2s;
}

.history-item:hover {
	border-color: #667eea;
	box-shadow: 0 2px 6px rgba(102, 126, 234, 0.1);
}

.history-header-item {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 0.5rem;
}

.history-date {
	font-size: 0.75rem;
	color: #666;
	font-weight: 500;
}

.history-file {
	font-size: 0.7rem;
	color: #999;
	background: #e9ecef;
	padding: 0.125rem 0.375rem;
	border-radius: 3px;
}

.history-preview {
	margin-bottom: 0.5rem;
}

.preview-text {
	font-size: 0.8rem;
	color: #666;
	line-height: 1.4;
}

.history-actions {
	display: flex;
	gap: 0.375rem;
}

.action-btn {
	padding: 0.25rem 0.5rem;
	border: none;
	border-radius: 4px;
	font-size: 0.75rem;
	cursor: pointer;
	transition: all 0.2s;
}

.view-btn {
	background: #667eea;
	color: white;
}

.view-btn:hover {
	background: #5568d3;
}

.delete-btn {
	background: #ff5252;
	color: white;
}

.delete-btn:hover {
	background: #ff1744;
}

.pagination {
	display: flex;
	justify-content: center;
	align-items: center;
	gap: 0.5rem;
	margin-top: 0.75rem;
	padding-top: 0.75rem;
	border-top: 1px solid #e0e0e0;
}

.page-btn {
	padding: 0.25rem 0.5rem;
	background: #667eea;
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	transition: all 0.2s;
	font-size: 0.875rem;
	min-width: 28px;
}

.page-btn:hover:not(:disabled) {
	background: #5568d3;
}

.page-btn:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

.page-info {
	font-size: 0.75rem;
	color: #666;
}
</style>
