#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
题库解析和管理模块
功能：
1. 解析TOP_generated.json文件
2. 将题目缓存在内存中
3. 标记题目是否有效
4. 通过id（字符串）访问题目
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass


@dataclass
class Question:
    """题目数据类"""

    id: str  # 题目ID（字符串）
    instruction: str  # 指令
    teacher: str  # 教授名字
    teacher_content: str  # 教授内容
    students: List[Dict[str, str]]  # 学生列表，每个元素包含name和content
    is_valid: bool  # 是否有效

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "instruction": self.instruction,
            "teacher": self.teacher,
            "teacher_content": self.teacher_content,
            "students": self.students,
            "is_valid": self.is_valid,
        }

    def to_evaluator_format(self) -> Dict:
        """转换为Evaluator类需要的格式（兼容旧格式）"""
        # 将students转换为字符串格式（兼容旧代码）
        students_text = []
        for student in self.students:
            student_name = student.get("name", "")
            student_content = student.get("content", "")
            if student_name and student_content:
                students_text.append(f"**Student ({student_name}):** {student_content}")

        # 构建teacher字符串（兼容旧格式）
        teacher_text = f"**Professor ({self.teacher}):** {self.teacher_content}"

        return {
            "instruction": self.instruction,
            "teacher": teacher_text,
            "students": students_text,
        }

    def to_markdown_format(self) -> Dict[str, str]:
        """
        转换为原始markdown格式（TPO.json格式）
        返回可以直接传给大模型的带markdown格式的字符串

        Returns:
            Dict包含:
            - instruction: 指令文本（带markdown格式）
            - teacher: 教授内容（带markdown格式，如 "**Professor (Doctor Diaz):** content"）
            - students: 学生回复列表（带markdown格式，如 ["**Student 1 (Name):** content", ...]）
        """
        # 构建teacher字符串（原始markdown格式）
        teacher_text = f"**Professor ({self.teacher}):** {self.teacher_content}"

        # 构建students列表（原始markdown格式，带序号）
        students_text = []
        for idx, student in enumerate(self.students, start=1):
            student_name = student.get("name", "")
            student_content = student.get("content", "")
            if student_name and student_content:
                students_text.append(
                    f"**Student {idx} ({student_name}):** {student_content}"
                )

        return {
            "instruction": self.instruction,
            "teacher": teacher_text,
            "students": students_text,
        }

    def to_markdown_string(self) -> str:
        """
        转换为完整的markdown格式字符串
        返回可以直接传给大模型的完整字符串

        Returns:
            str: 完整的markdown格式字符串
        """
        md_format = self.to_markdown_format()

        # 构建完整字符串
        parts = []
        parts.append(f"**Instruction:** {md_format['instruction']}")
        parts.append("")
        parts.append(md_format["teacher"])
        parts.append("")
        for student in md_format["students"]:
            parts.append(student)
            parts.append("")

        return "\n".join(parts)


class QuestionBank:
    """题库管理类"""

    def __init__(self, json_file: str = "TOP_generated.json"):
        """
        初始化题库

        Args:
            json_file: JSON文件路径，默认为TOP_generated.json
        """
        self.json_file = Path(json_file)
        self.questions: Dict[str, Question] = {}  # id -> Question
        self._load_questions()

    def _load_questions(self):
        """从JSON文件加载题目"""
        if not self.json_file.exists():
            raise FileNotFoundError(f"题库文件不存在: {self.json_file}")

        with open(self.json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.questions = {}
        for item in data:
            question_id = str(item.get("id", ""))
            if not question_id:
                continue  # 跳过没有id的题目

            instruction = item.get("instruction", "").strip()
            teacher = item.get("teacher", "").strip()
            teacher_content = item.get("teacher_content", "").strip()
            students = item.get("students", [])

            # 验证题目是否有效
            is_valid = self._validate_question(
                instruction, teacher, teacher_content, students
            )

            # 确保students格式正确
            normalized_students = self._normalize_students(students)

            question = Question(
                id=question_id,
                instruction=instruction,
                teacher=teacher,
                teacher_content=teacher_content,
                students=normalized_students,
                is_valid=is_valid,
            )

            self.questions[question_id] = question

    def _validate_question(
        self,
        instruction: str,
        teacher: str,
        teacher_content: str,
        students: List,
    ) -> bool:
        """
        验证题目是否有效

        有效条件：
        1. instruction不为空
        2. teacher不为空
        3. teacher_content不为空
        4. students至少有一个有效的学生（有name和content）
        """
        if not instruction or not teacher or not teacher_content:
            return False

        # 检查是否有至少一个有效的学生
        if not students:
            return False

        for student in students:
            if isinstance(student, dict):
                name = student.get("name", "").strip()
                content = student.get("content", "").strip()
                if name and content:
                    return True  # 至少有一个有效的学生即可
            elif isinstance(student, str):
                # 兼容旧格式（字符串格式）
                if student.strip():
                    return True

        return False

    def _normalize_students(self, students: List) -> List[Dict[str, str]]:
        """
        规范化students格式

        将students转换为统一的格式：List[Dict[str, str]]
        每个dict包含name和content字段
        """
        normalized = []
        for student in students:
            if isinstance(student, dict):
                # 已经是字典格式
                name = student.get("name", "").strip()
                content = student.get("content", "").strip()
                if name or content:  # 至少有一个字段不为空
                    normalized.append(
                        {
                            "name": name,
                            "content": content,
                        }
                    )
            elif isinstance(student, str):
                # 旧格式：字符串格式，需要解析
                # 格式: "**Student 1 (Name):** content"
                import re

                match = re.match(
                    r"\*\*Student\s+\d+\s*\(([^)]+)\):\s*(.*)", student, re.DOTALL
                )
                if match:
                    name = match.group(1).strip()
                    content = match.group(2).strip()
                    normalized.append(
                        {
                            "name": name,
                            "content": content,
                        }
                    )

        return normalized

    def reload(self):
        """重新加载题目（当文件更新时调用）"""
        self._load_questions()

    def get_question(
        self, question_id: str, only_valid: bool = True
    ) -> Optional[Question]:
        """
        根据ID获取题目

        Args:
            question_id: 题目ID（字符串）
            only_valid: 是否只返回有效题目，默认True

        Returns:
            Question对象，如果不存在或无效则返回None
        """
        question = self.questions.get(question_id)
        if not question:
            return None

        if only_valid and not question.is_valid:
            return None

        return question

    def get_question_list(
        self,
        only_valid: bool = True,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> Tuple[List[Dict], int]:
        """
        获取题目列表

        Args:
            only_valid: 是否只返回有效题目，默认True
            offset: 偏移量，默认0
            limit: 限制数量，None表示不限制

        Returns:
            (题目列表, 总数)
        """
        # 筛选题目
        filtered_questions = []
        for question in self.questions.values():
            if only_valid and not question.is_valid:
                continue
            filtered_questions.append(question)

        # 按id排序
        filtered_questions.sort(key=lambda q: int(q.id) if q.id.isdigit() else 0)

        total = len(filtered_questions)

        # 分页
        start = offset
        end = offset + limit if limit is not None else len(filtered_questions)
        paginated_questions = filtered_questions[start:end]

        # 转换为字典格式（简化版，只包含基本信息）
        result = []
        for question in paginated_questions:
            result.append(
                {
                    "id": question.id,
                    "instruction": (
                        question.instruction[:100] + "..."
                        if len(question.instruction) > 100
                        else question.instruction
                    ),
                    "teacher": question.teacher,
                    "is_valid": question.is_valid,
                    "student_count": len(question.students),
                }
            )

        return result, total

    def get_all_valid_ids(self) -> List[str]:
        """获取所有有效题目的ID列表"""
        return [q.id for q in self.questions.values() if q.is_valid]

    def get_question_markdown(
        self, question_id: str, only_valid: bool = True, as_string: bool = False
    ) -> Optional[Union[Dict[str, str], str]]:
        """
        获取题目的markdown格式

        Args:
            question_id: 题目ID（字符串）
            only_valid: 是否只返回有效题目，默认True
            as_string: 是否返回完整字符串格式，False返回字典格式

        Returns:
            Dict或str: markdown格式的题目数据，如果不存在或无效则返回None
        """
        question = self.get_question(question_id, only_valid=only_valid)
        if not question:
            return None

        if as_string:
            return question.to_markdown_string()
        else:
            return question.to_markdown_format()

    def get_statistics(self) -> Dict:
        """获取题库统计信息"""
        total = len(self.questions)
        valid_count = sum(1 for q in self.questions.values() if q.is_valid)
        invalid_count = total - valid_count

        return {
            "total": total,
            "valid": valid_count,
            "invalid": invalid_count,
        }


# 全局题库实例（单例模式）
_question_bank: Optional[QuestionBank] = None


def get_question_bank(json_file: str = "TOP_generated.json") -> QuestionBank:
    """
    获取全局题库实例（单例模式）

    Args:
        json_file: JSON文件路径，只在第一次调用时生效

    Returns:
        QuestionBank实例
    """
    global _question_bank
    if _question_bank is None:
        _question_bank = QuestionBank(json_file)
    return _question_bank


def reload_question_bank():
    """重新加载题库"""
    global _question_bank
    if _question_bank is not None:
        _question_bank.reload()
