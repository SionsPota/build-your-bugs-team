import os
import time
import yaml
import re
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, List, Optional

from telemetry import log_event
from question_bank import get_question_bank

load_dotenv()

PROMPT_DIR = Path(__file__).parent / "prompt"


def load_prompt(filename: str) -> str:
    """从文件中加载提示词"""
    file_path = PROMPT_DIR / filename
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


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
            # 提取区域内容（在END之前的部分）
            content = match.group(1).strip() if match.group(1) else ""
            items = []

            # 如果内容不为空，解析列表项
            if content:
                # 使用正则表达式匹配编号列表项
                item_pattern = r"^\d+\.\s+(.+?)(?=^\d+\.|$)"
                for item_match in re.finditer(
                    item_pattern, content, re.MULTILINE | re.DOTALL
                ):
                    item_text = item_match.group(1).strip()
                    if item_text:
                        items.append(item_text)

            # 即使内容为空，也设置空列表（表示区域存在但为空）
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
        """流式解析：接收一个文本块，返回解析出的结构化数据（如果有更新）
        持续解析：每次chunk都会尝试解析，即使区域未完成也会返回部分结果
        """
        self.buffer += chunk
        self.parsed_data["raw_text"] = self.buffer

        updated = False
        result = {}

        # 尝试解析各个部分（持续解析，即使未完成也返回部分结果）
        new_strengths = self._try_parse_section("STRENGTHS:", "strengths")
        if new_strengths is not None:
            # 比较列表内容是否发生变化（即使长度相同，内容可能不同）
            if new_strengths != self.parsed_data["strengths"]:
                self.parsed_data["strengths"] = new_strengths
                result["strengths"] = new_strengths
                updated = True

        new_weaknesses = self._try_parse_section("WEAKNESSES:", "weaknesses")
        if new_weaknesses is not None:
            if new_weaknesses != self.parsed_data["weaknesses"]:
                self.parsed_data["weaknesses"] = new_weaknesses
                result["weaknesses"] = new_weaknesses
                updated = True

        new_opportunities = self._try_parse_section("OPPORTUNITIES:", "opportunities")
        if new_opportunities is not None:
            if new_opportunities != self.parsed_data["opportunities"]:
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
        """尝试解析一个列表部分（可能不完整）
        持续解析：遇到header就开始填充，遇到1.开始填充第一项，遇到END结束填充该区域
        """
        # 查找 section_header 的位置
        header_pos = self.buffer.upper().find(section_header.upper())
        if header_pos == -1:
            return None

        # 提取header之后的所有内容（直到下一个区域header或END或文本末尾）
        # 查找下一个区域header的位置（用于确定当前区域的结束位置）
        next_headers = [
            self.buffer.upper().find("STRENGTHS:", header_pos + 1),
            self.buffer.upper().find("WEAKNESSES:", header_pos + 1),
            self.buffer.upper().find("OPPORTUNITIES:", header_pos + 1),
            self.buffer.upper().find("OVERVIEW:", header_pos + 1),
            self.buffer.upper().find("SCORE:", header_pos + 1),
        ]
        # 找到下一个header的位置（排除当前header）
        next_header_pos = min(
            [pos for pos in next_headers if pos > header_pos], default=len(self.buffer)
        )

        # 查找END标记的位置
        end_pos = self.buffer.upper().find("\nEND", header_pos)
        if end_pos == -1:
            end_pos = len(self.buffer)
        else:
            end_pos += 4  # 包含 "\nEND" 的长度

        # 确定当前区域的结束位置（取END和下一个header的较小值）
        section_end_pos = min(end_pos, next_header_pos)

        # 提取当前区域的内容
        section_start = header_pos + len(section_header)
        content = self.buffer[section_start:section_end_pos].strip()

        # 如果内容为空且没有遇到END，说明区域刚开始，返回空列表
        if not content:
            return []

        # 解析编号列表项（即使没有END也要解析已出现的内容）
        items = []
        # 匹配编号项：数字. 开头，直到下一个编号项或区域结束
        item_pattern = r"^\d+\.\s+(.+?)(?=^\d+\.|$|\nEND)"
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
        question: str = None,
        instruction: str = None,
        teacher: str = None,
        students: list = None,
    ):
        """初始化评估器
        Args:
            question: 题名（字符串），如果提供则从题库加载（优先级最高）
            instruction: 指令文本（当question未提供时使用）
            teacher: 教师问题（当question未提供时使用）
            students: 学生回复列表（当question未提供时使用）
        """
        self.question_markdown = None  # markdown格式字符串

        if question:
            # 从题库加载，使用新的markdown格式API
            question_bank = get_question_bank()
            question_obj = question_bank.get_question(question, only_valid=True)
            if not question_obj:
                raise ValueError(f"题目不存在或无效: {question}")
            # 使用新的markdown格式API获取完整字符串
            self.question_markdown = question_obj.to_markdown_string()
            # 同时保存结构化数据
            question_data = question_obj.to_evaluator_format()
            self.instruction = question_data["instruction"]
            self.teacher = question_data["teacher"]
            self.students = question_data["students"]
        else:
            # 直接传参
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

        # 如果使用question，优先使用markdown格式字符串
        if self.question_markdown:
            # 使用新的markdown格式API
            user_content = f"""{self.question_markdown}

**[Student's Response to Evaluate]**
{answer}"""
        else:
            # 兼容旧格式：手动构建
            students_text = "\n\n".join(self.students) if self.students else ""
            user_content = f"""**[Test Question Context]**
**Instruction:** {self.instruction}

{self.teacher}

{students_text}

**[Student's Response to Evaluate]**
{answer}"""

        prompt.append(
            {
                "role": "user",
                "content": user_content,
            }
        )
        return prompt

    def generate_response(self, answer: str, stream: bool = False):
        # 允许通过环境变量覆盖模型配置
        model_name = os.getenv("DASHSCOPE_MODEL", "mimo-v2-flash")
        base_url = os.getenv(
            "DASHSCOPE_BASE_URL", "https://api.xiaomimimo.com/v1"
        )
        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=base_url,
        )
        completion = _call_llm(
            client, model_name, self.generate_prompt(answer), stream
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
        model_name = os.getenv("DASHSCOPE_MODEL", "mimo-v2-flash")
        base_url = os.getenv(
            "DASHSCOPE_BASE_URL", "https://api.xiaomimimo.com/v1"
        )
        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=base_url,
        )
        completion = _call_llm(client, model_name, self.generate_prompt(), stream)
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
    evaluator = Evaluator(question="44")
    answer = "Claire presents a convincing argument indicating that the biggest mistake people make when buying tech products is mismatch of the product's capability and actual need. Admittedlty, mismatch would cause unneccesary cost wich is diffinetely bad. However, considering people can gradually develop their needs that match the product will, I am inclined that the biggest mistake is overlooking detailed information and making impulsive purchases. Nowadays, more and more companies lie to their consumers about the detailed configuration about their products. Mistakenly buying one machine that does not have the ideal capability you want will not only influence your work and study, but also waste your money. For example, my old grandpa bought a television impulsively simply because the client told him that the TV has cutting-edge technology while its resolution is actually awful. Finally my grandpa had to buy a new one for its bad experience."
    comment = evaluator.generate_response(answer)
    polisher = Polisher(answer, comment)
    polished_answer = polisher.generate_response()
    print(f"Comment: {comment}\n\nPolished Answer: {polished_answer}")
