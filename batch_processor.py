import json
from chat_manager import ChatManager
from tqdm import tqdm


class BatchProcessor:
    def __init__(self, config_path="config.yaml"):
        self.chat = ChatManager(config_path)

    def process_dataset(self, data, output_path):
        results = []
        for item in tqdm(data, desc="Processing"):
            try:
                # 重置上下文
                self.chat.reset_history()
                self.chat.clear_instructions()

                # 应用指令
                if item["instruction"]:
                    self.chat.generate_response(item["instruction"])

                # 生成响应
                response = self.chat.generate_response(item["input"])

                # 保存结果
                results.append({
                    **item,
                    "output": response,
                    "processing_info": {
                        "timestamp": self._current_time(),
                        "instructions": self.chat.get_active_instructions()
                    }
                })
            except Exception as e:
                results.append({
                    **item,
                    "output": f"处理失败: {str(e)}",
                    "error": True
                })

        self._save_results(results, output_path)

    def _current_time(self):
        from datetime import datetime
        return datetime.now().isoformat()

    def _save_results(self, results, output_path):
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存至 {output_path}")
        except Exception as e:
            print(f"保存失败: {str(e)}")