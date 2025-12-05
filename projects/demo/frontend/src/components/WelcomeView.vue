<template>
	<div class="welcome-container">
		<div class="welcome-header">
			<h1 class="welcome-title">欢迎使用 TOEFL 写作练习系统</h1>
			<p class="welcome-subtitle">
				选择题目开始练习，或查看历史记录继续之前的练习
			</p>
		</div>

		<div class="welcome-content">
			<!-- 用户信息卡片 -->
			<div class="info-card user-card">
				<h2 class="card-title">用户信息</h2>
				<div v-if="isAuthenticated && currentUser" class="user-info">
					<div class="user-avatar-large">
						{{ currentUser.username.charAt(0).toUpperCase() }}
					</div>
					<div class="user-details">
						<div class="user-name">{{ currentUser.username }}</div>
						<div class="user-email" v-if="currentUser.email">
							{{ currentUser.email }}
						</div>
					</div>
					<button @click="handleLogout" class="btn-logout">登出</button>
				</div>
				<div v-else class="user-info">
					<div class="user-avatar-large">?</div>
					<div class="user-details">
						<div class="user-name">未登录</div>
						<p class="login-hint">登录后可保存历史记录</p>
					</div>
					<button @click="handleLogin" class="btn-login">登录/注册</button>
				</div>
			</div>

			<!-- 题目列表卡片 -->
			<div class="info-card questions-card">
				<h2 class="card-title">选择题目</h2>
				<div v-if="loadingQuestions" class="loading">加载题目列表中...</div>
				<div v-else-if="questionFiles.length === 0" class="empty-state">
					暂无可用题目
				</div>
				<div v-else class="question-list">
					<div
						v-for="file in questionFiles"
						:key="file"
						class="question-item"
						@click="handleSelectQuestion(file)"
					>
						<div class="question-icon">📝</div>
						<div class="question-info">
							<div class="question-name">{{ file }}</div>
							<div class="question-hint">点击开始练习</div>
						</div>
						<div class="question-arrow">→</div>
					</div>
				</div>
			</div>

			<!-- 历史记录卡片 -->
			<div v-if="isAuthenticated" class="info-card history-card">
				<h2 class="card-title">最近历史记录</h2>
				<div v-if="loadingHistory" class="loading">加载历史记录中...</div>
				<div v-else-if="recentHistories.length === 0" class="empty-state">
					暂无历史记录
				</div>
				<div v-else class="history-list">
					<div
						v-for="history in recentHistories"
						:key="history.id"
						class="history-item"
						@click="handleViewHistory(history)"
					>
						<div class="history-icon">📚</div>
						<div class="history-info">
							<div class="history-title">
								{{ history.question || "未命名题目" }}
							</div>
							<div class="history-meta">
								<span v-if="history.score != null" class="history-score">
									评分：{{ history.score }}
								</span>
								<span>{{ formatDate(history.created_at) }}</span>
							</div>
						</div>
						<div class="history-arrow">→</div>
					</div>
				</div>
				<button
					v-if="recentHistories.length > 0"
					@click="handleViewAllHistory"
					class="btn-view-all"
				>
					查看全部历史记录
				</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getQuestionFileList } from "../api/service";
import { useAuth } from "../composables/useAuth";
import { getHistories } from "../api/history";
import type { History } from "../api/history";

// 用户认证
const { isAuthenticated, currentUser, logout } = useAuth();

// 响应式数据
const questionFiles = ref<string[]>([]);
const loadingQuestions = ref(false);
const recentHistories = ref<History[]>([]);
const loadingHistory = ref(false);

// 加载题目列表
const loadQuestionFiles = async () => {
	loadingQuestions.value = true;
	try {
		const result = await getQuestionFileList();
		questionFiles.value = result.files;
	} catch (error) {
		console.error("Failed to load question files:", error);
	} finally {
		loadingQuestions.value = false;
	}
};

// 加载历史记录
const loadHistory = async () => {
	if (!isAuthenticated.value) return;

	loadingHistory.value = true;
	try {
		const result = await getHistories(1, 5); // 获取最近5条
		recentHistories.value = result.histories || [];
	} catch (error) {
		console.error("Failed to load history:", error);
	} finally {
		loadingHistory.value = false;
	}
};

// 格式化日期
const formatDate = (dateString: string): string => {
	const date = new Date(dateString);
	return date.toLocaleString("zh-CN", {
		year: "numeric",
		month: "2-digit",
		day: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
	});
};

// 处理登录
const handleLogin = () => {
	emit("login");
};

// 处理登出
const handleLogout = () => {
	logout();
	recentHistories.value = [];
};

// 处理选择题目
const handleSelectQuestion = (file: string) => {
	emit("select-question", file);
};

// 处理查看历史记录
const handleViewHistory = (history: History) => {
	emit("view-history", history);
};

// 处理查看全部历史记录
const handleViewAllHistory = () => {
	emit("view-all-history");
};

// 组件挂载
onMounted(() => {
	loadQuestionFiles();
	if (isAuthenticated.value) {
		loadHistory();
	}
});

// 定义事件
const emit = defineEmits<{
	(e: "login"): void;
	(e: "select-question", file: string): void;
	(e: "view-history", history: History): void;
	(e: "view-all-history"): void;
}>();

// 暴露方法供父组件调用
defineExpose({
	refreshHistory: loadHistory,
});
</script>

<style scoped>
.welcome-container {
	width: 100%;
	min-height: 100vh;
	background: #f5f5f5;
	padding: 2rem 1rem;
	display: flex;
	flex-direction: column;
	align-items: center;
}

.welcome-header {
	text-align: center;
	margin-bottom: 2rem;
	color: #333;
}

.welcome-title {
	font-size: 2.5rem;
	font-weight: bold;
	margin-bottom: 10px;
	text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
}

.welcome-subtitle {
	font-size: 1.2rem;
	opacity: 0.9;
}

.welcome-content {
	width: 100%;
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
	gap: 1.5rem;
}

.info-card {
	background: white;
	border: 1px solid #ddd;
	border-radius: 4px;
	padding: 1.5rem;
}

.card-title {
	font-size: 1.5rem;
	font-weight: bold;
	margin-bottom: 20px;
	color: #333;
	border-bottom: 2px solid #667eea;
	padding-bottom: 10px;
}

.user-card {
	grid-column: span 1;
}

.user-info {
	display: flex;
	align-items: center;
	gap: 20px;
	flex-wrap: wrap;
}

.user-avatar-large {
	width: 60px;
	height: 60px;
	border-radius: 50%;
	background: #667eea;
	color: white;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 1.5rem;
	font-weight: bold;
	flex-shrink: 0;
}

.user-details {
	flex: 1;
	min-width: 150px;
}

.user-name {
	font-size: 1.3rem;
	font-weight: bold;
	color: #333;
	margin-bottom: 5px;
}

.user-email {
	font-size: 0.9rem;
	color: #666;
}

.login-hint {
	font-size: 0.9rem;
	color: #999;
	margin-top: 5px;
}

.btn-login,
.btn-logout {
	padding: 10px 20px;
	border: none;
	border-radius: 6px;
	font-weight: bold;
	cursor: pointer;
	transition: all 0.3s ease;
}

.btn-login {
	background: #667eea;
	color: white;
}

.btn-login:hover {
	background: #5568d3;
}

.btn-logout {
	background: #f5f5f5;
	color: #666;
}

.btn-logout:hover {
	background: #e0e0e0;
}

.questions-card {
	grid-column: span 1;
}

.question-list {
	display: flex;
	flex-direction: column;
	gap: 15px;
}

.question-item {
	display: flex;
	align-items: center;
	gap: 1rem;
	padding: 1rem;
	border: 1px solid #ddd;
	border-radius: 4px;
	cursor: pointer;
}

.question-item:hover {
	border-color: #667eea;
	background: #f5f5f5;
}

.question-icon {
	font-size: 2rem;
	flex-shrink: 0;
}

.question-info {
	flex: 1;
}

.question-name {
	font-size: 1.1rem;
	font-weight: bold;
	color: #333;
	margin-bottom: 5px;
}

.question-hint {
	font-size: 0.9rem;
	color: #999;
}

.question-arrow {
	font-size: 1.5rem;
	color: #667eea;
	flex-shrink: 0;
}

.history-card {
	grid-column: span 1;
}

.history-list {
	display: flex;
	flex-direction: column;
	gap: 15px;
	margin-bottom: 20px;
}

.history-item {
	display: flex;
	align-items: center;
	gap: 1rem;
	padding: 1rem;
	border: 1px solid #ddd;
	border-radius: 4px;
	cursor: pointer;
}

.history-item:hover {
	border-color: #667eea;
	background: #f5f5f5;
}

.history-icon {
	font-size: 2rem;
	flex-shrink: 0;
}

.history-info {
	flex: 1;
}

.history-title {
	font-size: 1rem;
	font-weight: bold;
	color: #333;
	margin-bottom: 5px;
}

.history-meta {
	font-size: 0.85rem;
	color: #999;
	display: flex;
	align-items: center;
	gap: 0.5rem;
	flex-wrap: wrap;
}

.history-score {
	font-size: 0.85rem;
	color: #667eea;
	font-weight: 600;
	background: #e8edff;
	padding: 0.125rem 0.375rem;
	border-radius: 3px;
}

.history-arrow {
	font-size: 1.5rem;
	color: #667eea;
	flex-shrink: 0;
}

.btn-view-all {
	width: 100%;
	padding: 0.75rem;
	background: #667eea;
	color: white;
	border: none;
	border-radius: 4px;
	font-weight: bold;
	cursor: pointer;
}

.btn-view-all:hover {
	background: #5568d3;
}

.loading,
.empty-state {
	text-align: center;
	padding: 40px 20px;
	color: #999;
	font-size: 1rem;
}

@media (max-width: 768px) {
	.welcome-content {
		grid-template-columns: 1fr;
	}

	.welcome-title {
		font-size: 2rem;
	}

	.welcome-subtitle {
		font-size: 1rem;
	}
}
</style>
