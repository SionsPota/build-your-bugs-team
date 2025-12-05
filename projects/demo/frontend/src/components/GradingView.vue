<template>
	<main class="grading-view">
		<GradingResults
			:answer="answer"
			:polished-answer="polishedAnswer"
			:parsed-comment="parsedComment"
			:current-stage="currentStage"
			:loading="loading"
			:error="error"
			:is-empty="isEmpty"
			@clear="handleClear"
		/>
	</main>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import GradingResults from "./grading/GradingResults.vue";
import {
	gradeAndPolishStreamById,
	getHistoryById,
	type StreamEvent,
} from "../api/service";
import type { History } from "../api/history";

const props = defineProps<{
	historyId?: string | number; // 历史记录ID（UUID或user_sequence），用于加载已有数据或流式接收新数据
}>();

// 响应式数据
const answer = ref("");
const polishedAnswer = ref("");
const loading = ref(false);
const error = ref<string | null>(null);
const currentStage = ref<"idle" | "evaluating" | "polishing" | "done">("idle");
const statusMessage = ref<string | null>(null);
const isEmpty = ref(false); // 是否为空历史记录

// 结构化评语数据
import type { ParsedComment } from "../api/service";
const parsedComment = ref<ParsedComment>({
	strengths: [],
	weaknesses: [],
	opportunities: [],
	overview: "",
	score: null,
	raw_text: "",
});

const emit = defineEmits<{
	(e: "clear"): void;
}>();

// 加载历史记录数据
const loadHistoryData = async (historyId: string | number) => {
	loading.value = true;
	error.value = null;
	isEmpty.value = false;
	try {
		const history: History = await getHistoryById(historyId);
		if (!history) {
			isEmpty.value = true;
			return;
		}
		answer.value = history.answer || "";
		polishedAnswer.value = history.polished_answer || "";
		// 使用后端返回的解析数据
		if ((history as any).parsed_comment) {
			parsedComment.value = (history as any).parsed_comment;
		} else {
			// 如果没有解析数据，重置为空
			parsedComment.value = {
				strengths: [],
				weaknesses: [],
				opportunities: [],
				overview: "",
				score: null,
				raw_text: "",
			};
		}
		currentStage.value = "done";
	} catch (err) {
		isEmpty.value = true;
		error.value = err instanceof Error ? err.message : "加载历史记录失败";
		console.error("Load history error:", err);
	} finally {
		loading.value = false;
	}
};

// 流式接收评分结果
const streamGradingResult = async (historyId: string | number) => {
	loading.value = true;
	error.value = null;
	polishedAnswer.value = "";
	currentStage.value = "idle";
	statusMessage.value = null;
	// 重置结构化评语数据
	parsedComment.value = {
		strengths: [],
		weaknesses: [],
		opportunities: [],
		overview: "",
		score: null,
		raw_text: "",
	};

	try {
		await gradeAndPolishStreamById(historyId, (event: StreamEvent) => {
			switch (event.type) {
				case "status":
					statusMessage.value = event.message || "";
					if (event.stage === "evaluating") {
						currentStage.value = "evaluating";
					} else if (event.stage === "polishing") {
						currentStage.value = "polishing";
					}
					break;

				case "comment_parsed":
					// 实时更新结构化数据
					if (event.data) {
						if (event.data.strengths !== undefined) {
							parsedComment.value.strengths = event.data.strengths;
						}
						if (event.data.weaknesses !== undefined) {
							parsedComment.value.weaknesses = event.data.weaknesses;
						}
						if (event.data.opportunities !== undefined) {
							parsedComment.value.opportunities = event.data.opportunities;
						}
						if (event.data.overview !== undefined) {
							parsedComment.value.overview = event.data.overview;
						}
						if (event.data.score !== undefined) {
							parsedComment.value.score = event.data.score;
						}
					}
					break;

				case "comment_complete":
					// 更新完整的结构化数据
					if (event.parsed_comment) {
						parsedComment.value = event.parsed_comment;
					}
					currentStage.value = "polishing";
					break;

				case "polished_chunk":
					if (event.content) {
						polishedAnswer.value += event.content;
					}
					break;

				case "polished_complete":
					if (event.polished_answer) {
						polishedAnswer.value = event.polished_answer;
					}
					break;

				case "history_saved":
					// 历史记录已保存
					break;

				case "done":
					currentStage.value = "done";
					statusMessage.value = "处理完成";
					loading.value = false;
					break;

				case "error":
					error.value = event.message || "处理过程中发生错误";
					loading.value = false;
					currentStage.value = "idle";
					break;
			}
		});
	} catch (err) {
		error.value =
			err instanceof Error ? err.message : "请求失败，请检查后端服务是否运行";
		console.error("Error:", err);
		loading.value = false;
		currentStage.value = "idle";
	}
};

const handleClear = () => {
	emit("clear");
};

// 监听 historyId 变化
watch(
	() => props.historyId,
	async (newId) => {
		if (newId) {
			isEmpty.value = false;
			// 先尝试加载历史记录数据
			try {
				const history: History = await getHistoryById(newId);
				if (!history) {
					isEmpty.value = true;
					loading.value = false;
					return;
				}
				answer.value = history.answer || "";
				// 如果已有完整数据，直接显示
				if (history.comment && history.polished_answer) {
					polishedAnswer.value = history.polished_answer;
					// 使用后端返回的解析数据
					if ((history as any).parsed_comment) {
						parsedComment.value = (history as any).parsed_comment;
					} else {
						// 如果没有解析数据，重置为空
						parsedComment.value = {
							strengths: [],
							weaknesses: [],
							opportunities: [],
							overview: "",
							score: null,
							raw_text: "",
						};
					}
					currentStage.value = "done";
					loading.value = false;
				} else {
					// 如果没有完整数据，开始流式接收
					await streamGradingResult(newId);
				}
			} catch (err) {
				// 如果加载失败，检查是否是404错误（记录不存在）
				if (err instanceof Error && err.message.includes("404")) {
					isEmpty.value = true;
					loading.value = false;
				} else {
					// 其他错误，尝试流式接收
					await streamGradingResult(newId);
				}
			}
		} else {
			// 没有historyId，显示空状态
			isEmpty.value = true;
			loading.value = false;
		}
	},
	{ immediate: true }
);

onMounted(() => {
	if (props.historyId) {
		// 组件挂载时如果有 historyId，加载数据
		loadHistoryData(props.historyId);
	} else {
		// 没有historyId，显示空状态
		isEmpty.value = true;
	}
});
</script>

<style scoped>
.grading-view {
	flex: 1;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}
</style>
