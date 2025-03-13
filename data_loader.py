import json
from pathlib import Path


class DataLoader:
    def __init__(self, input_path):
        self.input_path = Path(input_path)

    def load_data(self):
        try:
            # 处理多行JSON格式
            return self._load_json_lines()
        except Exception as e:
            raise RuntimeError(f"数据加载失败: {str(e)}")

    def _load_json_lines(self):
        """支持JSON Lines格式（每行一个JSON对象）"""
        data = []
        with open(self.input_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    item = json.loads(line)
                    data.append(self._process_item(item))
                except json.JSONDecodeError as e:
                    print(f"警告：跳过第{line_num}行无效JSON: {str(e)}")
        return data

    def _process_item(self, item):
        """统一数据格式处理（保持原有逻辑）"""
        return {
            "id": item.get("id", f"unknown_{hash(str(item))}"),
            "input": item["input"],
            "category": item.get("category", ""),
            "instruction": item.get("instruction", ""),
            "metadata": {
                "subset": item.get("subset", ""),
                "questions": item.get("decomposed_questions", []),
                "labels": item.get("question_label", [])
            }
        }