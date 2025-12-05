<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { getHistories, deleteHistory, type History } from "../api/history";
import { useAuth } from "../composables/useAuth";
import HistoryDetailOverlay from "./HistoryDetailOverlay.vue";

const router = useRouter();

const { isAuthenticated } = useAuth();

const histories = ref<History[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const currentPage = ref(1);
const totalPages = ref(1);
const total = ref(0);
const perPage = ref(20);

const selectedHistory = ref<History | null>(null);
const showDetail = ref(false);

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
		// 重新加载列表
		await loadHistories(currentPage.value);
		// 如果删除的是当前查看的记录，关闭详情
		if (selectedHistory.value?.id === historyId) {
			showDetail.value = false;
			selectedHistory.value = null;
		}
	} catch (err) {
		error.value = err instanceof Error ? err.message : "删除失败";
		console.error("Delete history error:", err);
	}
};

const handleViewDetail = (history: History) => {
	// 使用路由导航到历史记录详情页
	router.push(`/history/${history.id}`);
};

const handleCloseDetail = () => {
	showDetail.value = false;
	selectedHistory.value = null;
};

const handleDeleteFromOverlay = async (historyId: number) => {
	await handleDelete(historyId);
	// 删除后关闭overlay
	handleCloseDetail();
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

const truncateText = (text: string, maxLength: number = 100) => {
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
		selectedHistory.value = null;
		showDetail.value = false;
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
	<div class="history-panel">
		<div class="panel-header">
			<h3>历史记录</h3>
			<button
				v-if="isAuthenticated"
				class="refresh-btn"
				@click="loadHistories(currentPage)"
				:disabled="loading"
			>
				{{ loading ? "加载中..." : "刷新" }}
			</button>
		</div>

		<div v-if="!isAuthenticated" class="empty-state">
			<p>请先登录以查看历史记录</p>
		</div>

		<div v-else-if="loading && histories.length === 0" class="loading-state">
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
				<div class="history-header">
					<span class="history-date">{{ formatDate(history.created_at) }}</span>
					<div class="history-meta">
						<span v-if="history.score != null" class="history-score">
							评分：{{ history.score }}
						</span>
						<span class="history-file">{{ history.question }}</span>
					</div>
				</div>
				<div class="history-preview">
					<div class="preview-label">原文：</div>
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
					上一页
				</button>
				<span class="page-info">
					第 {{ currentPage }} / {{ totalPages }} 页（共 {{ total }} 条）
				</span>
				<button
					class="page-btn"
					@click="loadHistories(currentPage + 1)"
					:disabled="currentPage === totalPages || loading"
				>
					下一页
				</button>
			</div>
		</div>

		<!-- 历史记录详情 Overlay -->
		<HistoryDetailOverlay
			:show="showDetail"
			:history="selectedHistory"
			@close="handleCloseDetail"
			@delete="handleDeleteFromOverlay"
		/>
	</div>
</template>

<style scoped>
.history-panel {
	display: flex;
	flex-direction: column;
}

.panel-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 1rem 1.5rem;
	border-bottom: 1px solid rgba(0, 0, 0, 0.08);
	background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
}

.panel-header h3 {
	margin: 0;
	font-size: 1.1rem;
	font-weight: 700;
	color: #2d3748;
}

.refresh-btn {
	padding: 0.5rem 1rem;
	background: #667eea;
	color: white;
	border: none;
	border-radius: 6px;
	font-size: 0.875rem;
	cursor: pointer;
	transition: all 0.3s;
}

.refresh-btn:hover:not(:disabled) {
	background: #764ba2;
	transform: translateY(-1px);
}

.refresh-btn:disabled {
	opacity: 0.6;
	cursor: not-allowed;
}

.empty-state,
.loading-state,
.error-state {
	padding: 2rem;
	text-align: center;
	color: #666;
}

.error-state {
	color: #c62828;
}

.retry-btn {
	margin-top: 0.5rem;
	padding: 0.5rem 1rem;
	background: #667eea;
	color: white;
	border: none;
	border-radius: 6px;
	cursor: pointer;
}

.history-list {
	padding: 1rem;
}

.history-item {
	padding: 1rem;
	margin-bottom: 1rem;
	background: white;
	border: 1px solid #e0e0e0;
	border-radius: 8px;
	cursor: pointer;
	transition: all 0.3s;
}

.history-item:hover {
	border-color: #667eea;
	box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
	transform: translateY(-2px);
}

.history-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 0.75rem;
	gap: 1rem;
	flex-wrap: wrap;
}

.history-date {
	font-size: 0.875rem;
	color: #666;
	font-weight: 500;
	flex-shrink: 0;
}

.history-meta {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	flex-wrap: wrap;
	justify-content: flex-end;
	min-width: 0;
}

.history-score {
	font-size: 0.875rem;
	color: #667eea;
	font-weight: 600;
	background: #e8edff;
	padding: 0.25rem 0.5rem;
	border-radius: 4px;
}

.history-file {
	font-size: 0.75rem;
	color: #999;
	background: #f5f5f5;
	padding: 0.25rem 0.5rem;
	border-radius: 4px;
}

.history-preview {
	margin-bottom: 0.75rem;
}

.preview-label {
	font-size: 0.875rem;
	font-weight: 600;
	color: #333;
	margin-bottom: 0.25rem;
}

.preview-text {
	font-size: 0.875rem;
	color: #666;
	line-height: 1.5;
}

.history-actions {
	display: flex;
	gap: 0.5rem;
}

.action-btn {
	padding: 0.375rem 0.75rem;
	border: none;
	border-radius: 4px;
	font-size: 0.875rem;
	cursor: pointer;
	transition: all 0.2s;
}

.view-btn {
	background: #667eea;
	color: white;
}

.view-btn:hover {
	background: #764ba2;
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
	justify-content: space-between;
	align-items: center;
	padding: 1rem;
	border-top: 1px solid #e0e0e0;
}

.page-btn {
	padding: 0.5rem 1rem;
	background: #667eea;
	color: white;
	border: none;
	border-radius: 6px;
	cursor: pointer;
	transition: all 0.3s;
}

.page-btn:hover:not(:disabled) {
	background: #764ba2;
}

.page-btn:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

.page-info {
	font-size: 0.875rem;
	color: #666;
}
</style>
