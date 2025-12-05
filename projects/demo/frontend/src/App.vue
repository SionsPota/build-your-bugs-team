<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
	gradeAndPolishStream,
	healthCheck,
	downloadTelemetryLog,
	type StreamEvent,
} from "./api/service";
import { useAuth } from "./composables/useAuth";
import AuthModal from "./components/AuthModal.vue";
import Sidebar from "./components/Sidebar.vue";

const route = useRoute();
const router = useRouter();
const { isAuthenticated, currentUser, logout, ensureAuthenticated } = useAuth();

const showAuthModal = ref(false);

const loading = ref(false);
const error = ref<string | null>(null);
const isBackendHealthy = ref<boolean | null>(null);
const statusMessage = ref<string | null>(null);
const downloadingLog = ref(false);

// 根据路由计算当前视图
const currentView = computed<"welcome" | "grading" | "writing">(() => {
	if (route.name === "home") return "welcome";
	if (route.name === "write") return "writing";
	if (route.name === "history") return "grading";
	return "welcome";
});

// 是否显示侧边栏（非首页时显示）
const showSidebar = computed(() => route.name !== "home");

// 侧边栏展开状态，从localStorage读取
const getInitialSidebarState = (): boolean => {
	const saved = localStorage.getItem("sidebarExpanded");
	return saved ? saved === "true" : false; // 默认隐藏
};
const sidebarExpanded = ref<boolean>(getInitialSidebarState());

// 切换侧边栏展开状态
const toggleSidebar = () => {
	sidebarExpanded.value = !sidebarExpanded.value;
	localStorage.setItem("sidebarExpanded", String(sidebarExpanded.value));
};

const checkBackend = async () => {
	try {
		await healthCheck();
		isBackendHealthy.value = true;
	} catch (err) {
		isBackendHealthy.value = false;
		console.error("Backend health check failed:", err);
	}
};

const handleClear = () => {
	error.value = null;
	statusMessage.value = null;
	router.push("/home");
};

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

const handleLogout = () => {
	logout();
	router.push("/home");
};

const handleWritingSubmit = async (data: {
	text: string;
	wordCount: number;
	timeSpent: number;
	questionFile: string;
}) => {
	loading.value = true;
	error.value = null;

	try {
		// 发送评分请求，获取历史记录ID
		const historyId = await gradeAndPolishStream(
			data.text,
			data.questionFile,
			(event: StreamEvent) => {
				// 收到 history_id 后，导航到历史记录页面
				if (event.type === "history_id" && event.history_id) {
					router.push(`/history/${event.history_id}`);
					loading.value = false;
				}
			}
		);

		// 如果直接返回了ID（非流式情况）
		if (historyId !== null && historyId !== undefined) {
			router.push(`/history/${historyId}`);
		}
	} catch (err) {
		error.value =
			err instanceof Error ? err.message : "提交失败，请检查后端服务是否运行";
		console.error("Error:", err);
	} finally {
		loading.value = false;
	}
};

const handleWelcomeLogin = () => {
	showAuthModal.value = true;
};

const handleWelcomeSelectQuestion = (file: string) => {
	router.push({ path: "/write", query: { question: file } });
};

const handleWelcomeViewHistory = (history: any) => {
	if (history.id) {
		router.push(`/history/${history.id}`);
	}
};

const handleWelcomeViewAllHistory = () => {
	// 可以导航到第一个历史记录或保持当前逻辑
};

const handleViewChange = (view: "welcome" | "grading" | "writing") => {
	if (view === "welcome") {
		router.push("/home");
	} else if (view === "writing") {
		router.push("/write");
	}
	// 移除直接切换到评分界面的逻辑，评分界面只能通过历史记录访问
};

// 路由变化监听（如果需要可以在这里添加其他逻辑）

onMounted(async () => {
	checkBackend();
	await ensureAuthenticated();
});
</script>

<template>
	<div class="app-container">
		<!-- 侧边栏贴纸按钮 -->
		<button
			v-if="showSidebar"
			class="sidebar-toggle-btn"
			:class="{ expanded: sidebarExpanded }"
			@click="toggleSidebar"
			:title="sidebarExpanded ? '隐藏侧边栏' : '显示侧边栏'"
		>
			<span class="toggle-icon">{{ sidebarExpanded ? "◀" : "▶" }}</span>
		</button>

		<Sidebar
			v-if="showSidebar && sidebarExpanded"
			:is-authenticated="isAuthenticated"
			:current-user="currentUser"
			:backend-healthy="isBackendHealthy"
			:loading="loading"
			:status-message="statusMessage"
			:current-view="currentView"
			:downloading-log="downloadingLog"
			@login="showAuthModal = true"
			@logout="handleLogout"
			@check-backend="checkBackend"
			@view-change="handleViewChange"
			@download-log="handleDownloadLog"
		/>

		<router-view v-slot="{ Component, route: routeInfo }">
			<component
				:is="Component"
				:key="routeInfo.path"
				@submit="handleWritingSubmit"
				@clear="handleClear"
				@login="handleWelcomeLogin"
				@select-question="handleWelcomeSelectQuestion"
				@view-history="handleWelcomeViewHistory"
				@view-all-history="handleWelcomeViewAllHistory"
			/>
		</router-view>

		<AuthModal :show="showAuthModal" @close="showAuthModal = false" />
	</div>
</template>

<style scoped>
.app-container {
	display: flex;
	min-height: 100vh;
	background: #f5f5f5;
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
		"Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
	position: relative;
}

.sidebar-toggle-btn {
	position: fixed;
	left: 0;
	top: 50%;
	transform: translateY(-50%);
	width: 24px;
	height: 60px;
	background: #667eea;
	color: white;
	border: none;
	border-radius: 0 8px 8px 0;
	cursor: pointer;
	z-index: 1001;
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
	transition: left 0.3s ease, background 0.2s ease;
	padding: 0;
}

.sidebar-toggle-btn:hover {
	background: #5568d3;
}

.sidebar-toggle-btn.expanded {
	left: 250px; /* 侧边栏宽度为250px */
}

.toggle-icon {
	font-size: 12px;
	font-weight: bold;
	user-select: none;
	line-height: 1;
}
</style>
