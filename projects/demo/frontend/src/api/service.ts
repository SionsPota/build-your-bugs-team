// API 服务文件

export interface GradeAndPolishRequest {
	answer: string;
	question_file?: string;
}

export interface GradeAndPolishResponse {
	comment: string;
	polished_answer: string;
}

export interface ApiError {
	error: string;
}

// 流式事件类型
export interface StreamEvent {
	type:
		| "status"
		| "comment_chunk"
		| "comment_complete"
		| "polished_chunk"
		| "polished_complete"
		| "history_saved"
		| "history_id"
		| "done"
		| "error";
	stage?: "evaluating" | "polishing";
	message?: string;
	content?: string;
	comment?: string;
	polished_answer?: string;
	history_id?: number;
}

// 流式回调类型
export type StreamCallback = (event: StreamEvent) => void;

// API 基础地址配置
// 优先使用环境变量，否则使用代理路径
// 如果代理不工作，可以在 .env 文件中设置：VITE_API_BASE_URL=http://127.0.0.1:8000
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

/**
 * 获取认证头
 */
function getAuthHeaders(): HeadersInit {
	const token = localStorage.getItem("access_token");
	const headers: HeadersInit = {
		"Content-Type": "application/json",
	};
	if (token) {
		headers.Authorization = `Bearer ${token}`;
	}
	return headers;
}

/**
 * 流式调用评分和润色接口（返回历史记录ID）
 */
export async function gradeAndPolishStream(
	answer: string,
	questionFile: string = "test.yaml",
	onEvent: StreamCallback
): Promise<number | null> {
	const response = await fetch(`${API_BASE_URL}/grade_and_polish`, {
		method: "POST",
		headers: getAuthHeaders(),
		body: JSON.stringify({
			answer,
			question_file: questionFile,
		}),
	});

	if (!response.ok) {
		const error: ApiError = await response.json().catch(() => ({
			error: `HTTP error! status: ${response.status}`,
		}));
		throw new Error(error.error || `HTTP error! status: ${response.status}`);
	}

	if (!response.body) {
		throw new Error("Response body is null");
	}

	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let buffer = "";

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });
			const lines = buffer.split("\n\n");
			buffer = lines.pop() || ""; // 保留最后一个不完整的行

			for (const line of lines) {
				if (line.startsWith("data: ")) {
					try {
						const data = JSON.parse(line.substring(6));
						onEvent(data as StreamEvent);
						// 如果是 history_id 事件，返回ID
						if (data.type === "history_id" && data.history_id) {
							return data.history_id;
						}
					} catch (e) {
						console.error("Failed to parse SSE data:", e, line);
					}
				}
			}
		}
	} finally {
		reader.releaseLock();
	}
	return null;
}

/**
 * 通过历史记录ID流式获取评分结果
 * 支持UUID（字符串）或user_sequence（数字）作为ID
 */
export async function gradeAndPolishStreamById(
	historyId: string | number,
	onEvent: StreamCallback
): Promise<void> {
	const response = await fetch(
		`${API_BASE_URL}/grade_and_polish/${historyId}`,
		{
			method: "GET",
			headers: getAuthHeaders(),
		}
	);

	if (!response.ok) {
		const error: ApiError = await response.json().catch(() => ({
			error: `HTTP error! status: ${response.status}`,
		}));
		throw new Error(error.error || `HTTP error! status: ${response.status}`);
	}

	if (!response.body) {
		throw new Error("Response body is null");
	}

	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let buffer = "";

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });
			const lines = buffer.split("\n\n");
			buffer = lines.pop() || ""; // 保留最后一个不完整的行

			for (const line of lines) {
				if (line.startsWith("data: ")) {
					try {
						const data = JSON.parse(line.substring(6));
						onEvent(data as StreamEvent);
					} catch (e) {
						console.error("Failed to parse SSE data:", e, line);
					}
				}
			}
		}
	} finally {
		reader.releaseLock();
	}
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<{ status: string }> {
	const response = await fetch(`${API_BASE_URL}/health`);
	if (!response.ok) {
		throw new Error("Health check failed");
	}
	return await response.json();
}

/**
 * 下载遥测日志文件
 */
export async function downloadTelemetryLog(): Promise<Blob> {
	const response = await fetch(`${API_BASE_URL}/logs/telemetry`);
	if (!response.ok) {
		const error: ApiError = await response.json().catch(() => ({
			error: `HTTP error! status: ${response.status}`,
		}));
		throw new Error(error.error || `HTTP error! status: ${response.status}`);
	}
	return await response.blob();
}

/**
 * 题目数据接口
 */
export interface QuestionData {
	subject: string;
	professor: {
		name: string;
		avatar: string;
		prompt: string;
	};
	students: Array<{
		name: string;
		avatar: string;
		response: string;
	}>;
}

/**
 * 通过ID获取历史记录（从history API导入）
 */
export { getHistoryById } from "./history";

/**
 * 获取题目文件列表
 */
export async function getQuestionFileList(): Promise<{ files: string[] }> {
	const response = await fetch(`${API_BASE_URL}/question/list`);
	if (!response.ok) {
		const error: ApiError = await response.json().catch(() => ({
			error: `HTTP error! status: ${response.status}`,
		}));
		throw new Error(error.error || `HTTP error! status: ${response.status}`);
	}
	return await response.json();
}

/**
 * 获取题目数据
 * @param file 文件名，默认为 'test.yaml'
 */
export async function getQuestionData(
	file: string = "test.yaml"
): Promise<QuestionData> {
	const params = new URLSearchParams({ file });
	const response = await fetch(`${API_BASE_URL}/question?${params.toString()}`);
	if (!response.ok) {
		const error: ApiError = await response.json().catch(() => ({
			error: `HTTP error! status: ${response.status}`,
		}));
		throw new Error(error.error || `HTTP error! status: ${response.status}`);
	}
	return await response.json();
}
