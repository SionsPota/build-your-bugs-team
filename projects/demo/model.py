import os
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

from telemetry import log_event
from question_bank import get_question_bank

load_dotenv()

PROMPT_DIR = Path(__file__).parent / "prompt"


def load_prompt(filename: str) -> str:
    """从文件中加载提示词"""
    file_path = PROMPT_DIR / filename
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


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
    evaluator = Evaluator(question="44")
    answer = "Claire presents a convincing argument indicating that the biggest mistake people make when buying tech products is mismatch of the product's capability and actual need. Admittedlty, mismatch would cause unneccesary cost wich is diffinetely bad. However, considering people can gradually develop their needs that match the product will, I am inclined that the biggest mistake is overlooking detailed information and making impulsive purchases. Nowadays, more and more companies lie to their consumers about the detailed configuration about their products. Mistakenly buying one machine that does not have the ideal capability you want will not only influence your work and study, but also waste your money. For example, my old grandpa bought a television impulsively simply because the client told him that the TV has cutting-edge technology while its resolution is actually awful. Finally my grandpa had to buy a new one for its bad experience."
    comment = evaluator.generate_response(answer)
    polisher = Polisher(answer, comment)
    polished_answer = polisher.generate_response()
    print(f"Comment: {comment}\n\nPolished Answer: {polished_answer}")
