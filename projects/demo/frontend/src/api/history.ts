// 历史记录API服务

import type { ParsedComment } from "./service";

export interface History {
	id: number;
	global_id: string;
	user_sequence: number;
	user_id: number;
	answer: string;
	question: string;
	comment: string | null;
	polished_answer: string | null;
	score: number | null; // 总评分
	parsed_comment?: ParsedComment; // 后端解析后的结构化评语数据
	created_at: string;
}

export interface HistoryListResponse {
	histories: History[];
	pagination: {
		page: number;
		per_page: number;
		total: number;
		pages: number;
		has_next: boolean;
		has_prev: boolean;
	};
}

export interface ApiError {
	error: string;
}

// API 基础地址配置
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
 * 获取用户历史记录列表（分页）
 */
export async function getHistories(
	page: number = 1,
	perPage: number = 20
): Promise<HistoryListResponse> {
	const token = localStorage.getItem("access_token");
	if (!token) {
		throw new Error("未登录，请先登录");
	}

	const response = await fetch(
		`${API_BASE_URL}/history?page=${page}&per_page=${perPage}`,
		{
			method: "GET",
			headers: getAuthHeaders(),
		}
	);

	const result = await response.json();

	if (!response.ok) {
		// 如果是401或422，可能是token过期或无效
		if (response.status === 401 || response.status === 422) {
			// 清除无效的token
			localStorage.removeItem("access_token");
			localStorage.removeItem("refresh_token");
			localStorage.removeItem("user");
		}
		throw new Error((result as ApiError).error || "获取历史记录失败");
	}

	return result as HistoryListResponse;
}

/**
 * 获取单条历史记录详情
 * 支持UUID（字符串）或user_sequence（数字）作为ID
 */
export async function getHistoryById(
	historyId: string | number
): Promise<History> {
	const response = await fetch(`${API_BASE_URL}/history/${historyId}`, {
		method: "GET",
		headers: getAuthHeaders(),
	});

	const result = await response.json();

	if (!response.ok) {
		throw new Error((result as ApiError).error || "获取历史记录失败");
	}

	return (result as { history: History }).history;
}

/**
 * 删除历史记录
 * 支持UUID（字符串）或user_sequence（数字）作为ID
 */
export async function deleteHistory(historyId: string | number): Promise<void> {
	const response = await fetch(`${API_BASE_URL}/history/${historyId}`, {
		method: "DELETE",
		headers: getAuthHeaders(),
	});

	const result = await response.json();

	if (!response.ok) {
		throw new Error((result as ApiError).error || "删除历史记录失败");
	}
}
