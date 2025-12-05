<template>
	<aside class="sidebar">
		<!-- 标题 -->
		<div class="sidebar-header">
			<h2>TOEFL 写作评分</h2>
		</div>

		<!-- 主要内容区域（可滚动） -->
		<div class="sidebar-content">
			<!-- 历史记录列表 -->
			<HistoryList v-if="isAuthenticated" ref="historyListRef" />

			<!-- 调试状态（默认隐藏） -->
			<div v-if="showDebug" class="debug-section">
				<div class="divider"></div>
				<StatusSection
					:backend-healthy="backendHealthy"
					:loading="loading"
					:status-message="statusMessage"
					@check-backend="$emit('check-backend')"
				/>

				<ActionSection
					:current-view="currentView"
					@view-change="$emit('view-change', $event)"
					@check-backend="$emit('check-backend')"
					@download-log="$emit('download-log')"
					:downloading-log="downloadingLog"
				/>
			</div>
		</div>

		<!-- 用户配置（贴底部） -->
		<div class="sidebar-footer">
			<UserSection
				:is-authenticated="isAuthenticated"
				:current-user="currentUser"
				@login="$emit('login')"
				@logout="$emit('logout')"
				@view-change="$emit('view-change', $event)"
			/>
		</div>
	</aside>
</template>

<script setup lang="ts">
import { ref } from "vue";
import UserSection from "./sidebar/UserSection.vue";
import StatusSection from "./sidebar/StatusSection.vue";
import ActionSection from "./sidebar/ActionSection.vue";
import HistoryList from "./HistoryList.vue";

defineProps<{
	isAuthenticated: boolean;
	currentUser: any;
	backendHealthy: boolean | null;
	loading: boolean;
	statusMessage: string | null;
	currentView: "welcome" | "grading" | "writing";
	downloadingLog: boolean;
}>();

const historyListRef = ref<{
	loadHistories: (page?: number) => Promise<void>;
} | null>(null);

// 调试状态默认隐藏
const showDebug = ref(false);

const emit = defineEmits<{
	(e: "login"): void;
	(e: "logout"): void;
	(e: "check-backend"): void;
	(e: "view-change", view: "welcome" | "grading" | "writing"): void;
	(e: "download-log"): void;
}>();

defineExpose({
	historyListRef,
});
</script>

<style scoped>
.sidebar {
	background: #fff;
	border-right: 1px solid #ddd;
	display: flex;
	flex-direction: column;
	width: 250px;
	flex-shrink: 0;
	height: 100vh;
	overflow: hidden;
}

.sidebar-header {
	padding: 1rem;
	border-bottom: 1px solid #ddd;
	flex-shrink: 0;
}

.sidebar-header h2 {
	margin: 0;
	font-size: 1rem;
	font-weight: 600;
}

.sidebar-content {
	flex: 1;
	padding: 1rem;
	overflow-y: auto;
	display: flex;
	flex-direction: column;
	min-height: 0;
}

.debug-section {
	display: flex;
	flex-direction: column;
}

.sidebar-footer {
	padding: 1rem;
	border-top: 1px solid #ddd;
	flex-shrink: 0;
	background: #fff;
}

.divider {
	border-top: 1px solid #ddd;
	margin: 1rem 0;
	flex-shrink: 0;
}
</style>
