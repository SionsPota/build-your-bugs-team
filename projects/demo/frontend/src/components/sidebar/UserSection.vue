<template>
	<div class="user-section">
		<div v-if="isAuthenticated && currentUser" class="user-info">
			<div class="user-avatar">
				{{ currentUser.username.charAt(0).toUpperCase() }}
			</div>
			<div class="user-details">
				<div class="user-name">{{ currentUser.username }}</div>
				<div class="user-email" v-if="currentUser.email">
					{{ currentUser.email }}
				</div>
			</div>
		</div>
		<div v-else class="user-info">
			<div class="user-avatar">?</div>
			<div class="user-details">
				<div class="user-name">未登录</div>
			</div>
		</div>
		<div class="user-actions">
			<button v-if="!isAuthenticated" @click="$emit('login')" class="btn">
				登录/注册
			</button>
			<template v-else>
				<button @click="$emit('view-change', 'welcome')" class="btn">
					主面板
				</button>
				<button @click="$emit('logout')" class="btn">登出</button>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
defineProps<{
	isAuthenticated: boolean;
	currentUser: any;
}>();

defineEmits<{
	(e: "login"): void;
	(e: "logout"): void;
	(e: "view-change", view: "welcome" | "grading" | "writing"): void;
}>();
</script>

<style scoped>
.user-section {
	padding: 0;
}

.user-info {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	margin-bottom: 1rem;
}

.user-avatar {
	width: 40px;
	height: 40px;
	border-radius: 50%;
	background: #667eea;
	color: white;
	display: flex;
	align-items: center;
	justify-content: center;
	font-weight: bold;
	flex-shrink: 0;
}

.user-details {
	flex: 1;
	min-width: 0;
}

.user-name {
	font-weight: 600;
	color: #333;
	font-size: 0.9rem;
}

.user-email {
	font-size: 0.75rem;
	color: #666;
}

.user-actions {
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
}

.btn {
	padding: 0.5rem;
	border: 1px solid #ddd;
	background: #fff;
	cursor: pointer;
	border-radius: 4px;
}

.btn:hover {
	background: #f5f5f5;
}

.btn.active {
	background: #e3f2fd;
	border-color: #667eea;
}
</style>
