import { createRouter, createWebHistory } from "vue-router";
import WelcomeView from "../components/WelcomeView.vue";
import TOEFLWritingView from "../components/TOEFLWritingView.vue";
import GradingView from "../components/GradingView.vue";

const router = createRouter({
	history: createWebHistory(),
	routes: [
		{
			path: "/",
			redirect: "/home",
		},
		{
			path: "/home",
			name: "home",
			component: WelcomeView,
		},
		{
			path: "/write",
			name: "write",
			component: TOEFLWritingView,
			props: (route) => ({
				initialQuestionFile: (route.query.question as string) || "test.yaml",
			}),
		},
		{
			path: "/history/:id",
			name: "history",
			component: GradingView,
			props: (route) => ({
				// 支持UUID（字符串）或user_sequence（数字）
				historyId: route.params.id,
			}),
		},
	],
});

export default router;
