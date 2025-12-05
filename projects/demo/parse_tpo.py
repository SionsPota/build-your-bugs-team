#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TPO.json 数据解析脚本
功能：
1. 清理markdown格式
2. 优化数据结构：teacher下面即名字，添加teacher_content字段
3. students下使用Object列表，采用 {name:"name",content:"content"}的格式
"""

import json
import re


def clean_markdown(text):
    """清理markdown格式"""
    if not text:
        return text

    # 移除markdown加粗标记 **
    text = text.replace("**", "")

    # 清理instruction中的列表标记（保留内容，移除*但保留空格缩进）
    # 将 "*   " 或 "*    " 替换为换行加相应数量的空格
    # 匹配 "*" 后跟多个空格，替换为换行加这些空格
    text = re.sub(r"\*(\s+)", r"\n\1", text)

    return text.strip()


def extract_teacher_info(teacher_text):
    """
    从teacher字段中提取教授名字和内容
    格式: "**Professor (Doctor Diaz):** content"
    返回: (name, content)
    """
    if not teacher_text or teacher_text.strip() == "":
        return "", ""

    # 移除markdown标记
    teacher_text = teacher_text.replace("**", "")

    # 匹配格式: "Professor (Doctor Name): content"
    match = re.match(r"Professor\s*\(([^)]+)\):\s*(.*)", teacher_text, re.DOTALL)

    if match:
        name = match.group(1).strip()
        content = match.group(2).strip()
        return name, content
    else:
        # 如果没有匹配到，尝试其他格式
        # 如果已经是清理后的格式，直接返回
        if ":" in teacher_text:
            parts = teacher_text.split(":", 1)
            name = parts[0].strip()
            content = parts[1].strip() if len(parts) > 1 else ""
            return name, content
        else:
            return teacher_text.strip(), ""


def extract_student_info(student_text):
    """
    从student字符串中提取学生名字和讨论内容
    格式: "**Student 1 (Name):** content" 或 "**Student 2 (Name):** content"
    返回: {"name": "Name", "content": "content"}
    """
    if not student_text or student_text.strip() == "":
        return {"name": "", "content": ""}

    # 移除markdown标记
    student_text = student_text.replace("**", "")

    # 匹配格式: "Student 1 (Name): content" 或 "Student 2 (Name): content"
    match = re.match(r"Student\s+\d+\s*\(([^)]+)\):\s*(.*)", student_text, re.DOTALL)

    if match:
        name = match.group(1).strip()
        content = match.group(2).strip()
        return {"name": name, "content": content}
    else:
        # 如果没有匹配到，尝试其他格式
        if ":" in student_text:
            parts = student_text.split(":", 1)
            name = parts[0].strip()
            content = parts[1].strip() if len(parts) > 1 else ""
            return {"name": name, "content": content}
        else:
            return {"name": "", "content": student_text.strip()}


def parse_tpo_data(input_file, output_file):
    """
    解析TPO.json文件并生成清理后的数据

    Args:
        input_file: 输入的TPO.json文件路径
        output_file: 输出的TOP_generated.json文件路径
    """
    # 读取输入文件
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 处理每个条目
    processed_data = []
    for item in data:
        processed_item = {
            "id": item.get("id"),
            "instruction": clean_markdown(item.get("instruction", "")),
        }

        # 处理teacher字段
        teacher_text = item.get("teacher", "")
        teacher_name, teacher_content = extract_teacher_info(teacher_text)
        processed_item["teacher"] = teacher_name
        processed_item["teacher_content"] = teacher_content

        # 处理students字段
        students = item.get("students", [])
        processed_students = []
        for student_text in students:
            student_info = extract_student_info(student_text)
            # 只添加有名字或内容的学生
            if student_info["name"] or student_info["content"]:
                processed_students.append(student_info)

        processed_item["students"] = processed_students

        processed_data.append(processed_item)

    # 写入输出文件
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed_data, f, ensure_ascii=False, indent="\t")

    print(f"成功解析 {len(processed_data)} 条数据")
    print(f"输出文件: {output_file}")


if __name__ == "__main__":
    input_file = "TPO.json"
    output_file = "TOP_generated.json"

    try:
        parse_tpo_data(input_file, output_file)
        print("解析完成！")
    except FileNotFoundError:
        print(f"错误: 找不到文件 {input_file}")
    except json.JSONDecodeError as e:
        print(f"错误: JSON解析失败 - {e}")
    except Exception as e:
        print(f"错误: {e}")
