import os
import time
import yaml
import re
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, List, Optional

from telemetry import log_event

load_dotenv()

PROMPT_DIR = Path(__file__).parent / "prompt"
PROBLEMS_DIR = Path(__file__).parent / "problems"


def load_prompt(filename: str) -> str:
    """从文件中加载提示词"""
    file_path = PROMPT_DIR / filename
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_question(yaml_file: str) -> dict:
    """从 YAML 文件加载题目数据
    Args:
        yaml_file: YAML 文件名（如 "test.yaml"）

    Returns:
        dict: 包含 instruction, teacher, students 的字典
    """
    file_path = PROBLEMS_DIR / yaml_file
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return {
        "instruction": data.get("instruction", ""),
        "teacher": data.get("teacher", ""),
        "students": data.get("students", []),
    }


class CommentParser:
    """解析结构化评语的解析器"""

    def __init__(self):
        self.buffer = ""
        self.parsed_data = {
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "overview": "",
            "score": None,
            "raw_text": "",
        }
        self.current_section = None
        self.current_items = []
        self.current_item_text = ""
        self.in_overview = False
        self.overview_text = ""
        self.score_found = False

    def parse_complete(self, text: str) -> Dict:
        """解析完整的评语文本"""
        self.buffer = text
        self.parsed_data["raw_text"] = text

        # 解析各个部分
        self._parse_section("STRENGTHS:", "strengths")
        self._parse_section("WEAKNESSES:", "weaknesses")
        self._parse_section("OPPORTUNITIES:", "opportunities")
        self._parse_overview()
        self._parse_score()

        return self.parsed_data

    def _parse_section(self, section_header: str, section_key: str):
        """解析一个列表部分（STRENGTHS/WEAKNESSES/OPPORTUNITIES）"""
        pattern = rf"{re.escape(section_header)}\s*\n(.*?)\nEND"
        match = re.search(pattern, self.buffer, re.DOTALL | re.IGNORECASE)

        if match:
            content = match.group(1).strip()
            items = []

            # 使用正则表达式匹配编号列表项
            item_pattern = r"^\d+\.\s+(.+?)(?=^\d+\.|$)"
            for item_match in re.finditer(
                item_pattern, content, re.MULTILINE | re.DOTALL
            ):
                item_text = item_match.group(1).strip()
                if item_text:
                    items.append(item_text)

            self.parsed_data[section_key] = items

    def _parse_overview(self):
        """解析 OVERVIEW 部分"""
        pattern = r"OVERVIEW:\s*\n(.*?)\nEND"
        match = re.search(pattern, self.buffer, re.DOTALL | re.IGNORECASE)

        if match:
            self.parsed_data["overview"] = match.group(1).strip()

    def _parse_score(self):
        """解析 SCORE 部分"""
        pattern = r"SCORE:\s*\n\[(\d+)\]"
        match = re.search(pattern, self.buffer, re.IGNORECASE)

        if match:
            try:
                self.parsed_data["score"] = int(match.group(1))
            except ValueError:
                pass

    def feed_chunk(self, chunk: str) -> Optional[Dict]:
        """流式解析：接收一个文本块，返回解析出的结构化数据（如果有更新）"""
        self.buffer += chunk
        self.parsed_data["raw_text"] = self.buffer

        updated = False
        result = {}

        # 尝试解析各个部分
        new_strengths = self._try_parse_section("STRENGTHS:", "strengths")
        if new_strengths is not None and new_strengths != self.parsed_data["strengths"]:
            self.parsed_data["strengths"] = new_strengths
            result["strengths"] = new_strengths
            updated = True

        new_weaknesses = self._try_parse_section("WEAKNESSES:", "weaknesses")
        if (
            new_weaknesses is not None
            and new_weaknesses != self.parsed_data["weaknesses"]
        ):
            self.parsed_data["weaknesses"] = new_weaknesses
            result["weaknesses"] = new_weaknesses
            updated = True

        new_opportunities = self._try_parse_section("OPPORTUNITIES:", "opportunities")
        if (
            new_opportunities is not None
            and new_opportunities != self.parsed_data["opportunities"]
        ):
            self.parsed_data["opportunities"] = new_opportunities
            result["opportunities"] = new_opportunities
            updated = True

        new_overview = self._try_parse_overview()
        if new_overview is not None and new_overview != self.parsed_data["overview"]:
            self.parsed_data["overview"] = new_overview
            result["overview"] = new_overview
            updated = True

        new_score = self._try_parse_score()
        if new_score is not None and new_score != self.parsed_data["score"]:
            self.parsed_data["score"] = new_score
            result["score"] = new_score
            updated = True

        return result if updated else None

    def _try_parse_section(
        self, section_header: str, section_key: str
    ) -> Optional[List[str]]:
        """尝试解析一个列表部分（可能不完整）"""
        # 查找 section_header 的位置
        header_pos = self.buffer.upper().find(section_header.upper())
        if header_pos == -1:
            return None

        # 查找 END 标记
        end_pos = self.buffer.upper().find("\nEND", header_pos)

        if end_pos == -1:
            # 如果还没找到 END，尝试解析当前内容（可能不完整）
            content = self.buffer[header_pos + len(section_header) :].strip()
        else:
            content = self.buffer[header_pos + len(section_header) : end_pos].strip()

        if not content:
            return []

        items = []
        item_pattern = r"^\d+\.\s+(.+?)(?=^\d+\.|$)"
        for item_match in re.finditer(item_pattern, content, re.MULTILINE | re.DOTALL):
            item_text = item_match.group(1).strip()
            if item_text:
                items.append(item_text)

        return items

    def _try_parse_overview(self) -> Optional[str]:
        """尝试解析 OVERVIEW 部分（可能不完整）"""
        pattern = r"OVERVIEW:\s*\n(.*?)(?:\nEND|$)"
        match = re.search(pattern, self.buffer, re.DOTALL | re.IGNORECASE)

        if match:
            return match.group(1).strip()
        return None

    def _try_parse_score(self) -> Optional[int]:
        """尝试解析 SCORE 部分"""
        pattern = r"SCORE:\s*\n\[(\d+)\]"
        match = re.search(pattern, self.buffer, re.IGNORECASE)

        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None

    def get_parsed_data(self) -> Dict:
        """获取当前解析的数据"""
        return self.parsed_data.copy()


class Evaluator:
    def __init__(
        self,
        instruction: str = None,
        teacher: str = None,
        students: list = None,
        question_file: str = None,
    ):
        """初始化评估器
        Args:
            instruction: 指令文本
            teacher: 教师问题
            students: 学生回复列表
            question_file: YAML 文件名，如果提供则从文件加载（优先级高于直接传参）
        """
        if question_file:
            question_data = load_question(question_file)
            self.instruction = question_data["instruction"]
            self.teacher = question_data["teacher"]
            self.students = question_data["students"]
        else:
            self.instruction = instruction
            self.teacher = teacher
            self.students = students or []

        self.system_prompt = load_prompt("system_prompt_Evaluate.txt")
        self.few_shot_examples = self._load_few_shot_examples()

    def _load_few_shot_examples(self):
        """加载 few-shot learning 示例"""
        examples = []
        try:
            user_1 = load_prompt("user_prompt_1.txt")
            assistant_1 = load_prompt("assistant_prompt_1.txt")
            if (
                user_1
                and not user_1.startswith("#")
                and assistant_1
                and not assistant_1.startswith("#")
            ):
                examples.append(
                    [
                        {"role": "user", "content": user_1},
                        {"role": "assistant", "content": assistant_1},
                    ]
                )
        except FileNotFoundError:
            pass
        try:
            user_2 = load_prompt("user_prompt_2.txt")
            assistant_2 = load_prompt("assistant_prompt_2.txt")
            if (
                user_2
                and not user_2.startswith("#")
                and assistant_2
                and not assistant_2.startswith("#")
            ):
                examples.append(
                    [
                        {"role": "user", "content": user_2},
                        {"role": "assistant", "content": assistant_2},
                    ]
                )
        except FileNotFoundError:
            pass
        return examples

    def generate_prompt(self, answer: str):
        prompt = []
        prompt.append({"role": "system", "content": self.system_prompt})
        for example_pair in self.few_shot_examples:
            prompt.extend(example_pair)

        # 构建学生回复部分
        students_text = ""
        for i, student in enumerate(self.students, 1):
            students_text += f"{student}\n\n"

        prompt.append(
            {
                "role": "user",
                "content": f"""**[Test Question Context]**
        **Instruction:** {self.instruction}

{self.teacher}

{students_text}**[Student's Response to Evaluate]**
{answer}""",
            }
        )
        return prompt

    def generate_response(self, answer: str, stream: bool = False):
        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        completion = _call_llm(
            client, "qwen-plus", self.generate_prompt(answer), stream
        )
        if stream:
            return completion
        return completion.choices[0].message.content


class Polisher:
    def __init__(self, answer: str, comment: str):
        self.answer = answer
        self.comment = comment
        self.system_prompt = load_prompt("system_prompt_Polish.txt")

    def generate_prompt(self):
        prompt = []
        prompt.append({"role": "system", "content": self.system_prompt})
        prompt.append(
            {
                "role": "user",
                "content": f"""**[Original Essay]**
{self.answer}

**[Comment]**
{self.comment}
""",
            }
        )
        return prompt

    def generate_response(self, stream: bool = False):
        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        completion = _call_llm(client, "qwen-plus", self.generate_prompt(), stream)
        if stream:
            return completion
        return completion.choices[0].message.content


def _call_llm(client: OpenAI, model_name: str, messages, stream: bool = False):
    """调用 LLM 并记录基础遥测（时延/错误）。"""
    try:
        from flask import g

        request_id = getattr(g, "request_id", None)
    except Exception:
        request_id = None

    start = time.perf_counter()
    log_event(
        "llm.call.start", request_id=request_id, llm_model=model_name, stream=stream
    )
    try:
        completion = client.chat.completions.create(
            model=model_name, messages=messages, stream=stream
        )
    except Exception as e:
        log_event(
            "llm.call.error",
            request_id=request_id,
            llm_model=model_name,
            llm_latency_ms=int((time.perf_counter() - start) * 1000),
            llm_error=str(e),
            stream=stream,
        )
        raise

    if not stream:
        log_event(
            "llm.call.success",
            request_id=request_id,
            llm_model=model_name,
            llm_latency_ms=int((time.perf_counter() - start) * 1000),
            stream=False,
        )
        return completion

    def _stream_wrapper():
        try:
            for chunk in completion:
                yield chunk
            log_event(
                "llm.call.success",
                request_id=request_id,
                llm_model=model_name,
                llm_latency_ms=int((time.perf_counter() - start) * 1000),
                stream=True,
            )
        except Exception as e:
            log_event(
                "llm.call.error",
                request_id=request_id,
                llm_model=model_name,
                llm_latency_ms=int((time.perf_counter() - start) * 1000),
                llm_error=str(e),
                stream=True,
            )
            raise

    return _stream_wrapper()


if __name__ == "__main__":
    evaluator = Evaluator(question_file="test.yaml")
    answer = "Claire presents a convincing argument indicating that the biggest mistake people make when buying tech products is mismatch of the product's capability and actual need. Admittedlty, mismatch would cause unneccesary cost wich is diffinetely bad. However, considering people can gradually develop their needs that match the product will, I am inclined that the biggest mistake is overlooking detailed information and making impulsive purchases. Nowadays, more and more companies lie to their consumers about the detailed configuration about their products. Mistakenly buying one machine that does not have the ideal capability you want will not only influence your work and study, but also waste your money. For example, my old grandpa bought a television impulsively simply because the client told him that the TV has cutting-edge technology while its resolution is actually awful. Finally my grandpa had to buy a new one for its bad experience."
    comment = evaluator.generate_response(answer)
    polisher = Polisher(answer, comment)
    polished_answer = polisher.generate_response()
    print(f"Comment: {comment}\n\nPolished Answer: {polished_answer}")
