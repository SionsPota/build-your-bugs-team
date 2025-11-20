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
		| "done"
		| "error";
	stage?: "evaluating" | "polishing";
	message?: string;
	content?: string;
	comment?: string;
	polished_answer?: string;
}

// 流式回调类型
export type StreamCallback = (event: StreamEvent) => void;

// API 基础地址配置
// 优先使用环境变量，否则使用代理路径
// 如果代理不工作，可以在 .env 文件中设置：VITE_API_BASE_URL=http://127.0.0.1:8000
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

/**
 * 流式调用评分和润色接口
 */
export async function gradeAndPolishStream(
	answer: string,
	questionFile: string = "test.yaml",
	onEvent: StreamCallback
): Promise<void> {
	const response = await fetch(`${API_BASE_URL}/grade_and_polish`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
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
						const data = JSON.parse(line.slice(6));
						onEvent(data);
					} catch (e) {
						console.error("Failed to parse SSE data:", e, line);
					}
				}
			}
		}

		// 处理剩余的 buffer
		if (buffer.trim()) {
			if (buffer.startsWith("data: ")) {
				try {
					const data = JSON.parse(buffer.slice(6));
					onEvent(data);
				} catch (e) {
					console.error("Failed to parse SSE data:", e, buffer);
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
