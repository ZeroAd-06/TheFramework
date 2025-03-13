import yaml
from openai import OpenAI
from pathlib import Path
import json
import time


class ChatManager:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.client = OpenAI(
            base_url=self.config["api"]["base_url"],
            api_key=self.config["api"]["api_key"]
        )
        self.conversation_history = []
        self.active_instructions = []

    def _load_config(self, config_path):
        try:
            with open(config_path, "r", encoding="UTF-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"加载配置文件失败: {str(e)}")

    def generate_response(self, user_input):
        self._add_message("user", user_input)
        self._check_instruction_conflicts(user_input)
        self._extract_instructions(user_input)

        final_response = None
        retry_count = 0

        while retry_count <= self.config["validation"]["max_retries"]:
            try:
                # 生成/修正响应
                response = self._generate_single_response()

                # 执行验证
                if self.config["validation"]["enable"]:
                    validation = self._validate_response(response)
                    if validation["valid"]:
                        final_response = response
                        break
                else:
                    final_response = response
                    break

                # 处理验证失败
                print(f"验证失败，尝试修正（{retry_count + 1}/{self.config['validation']['max_retries']}）")
                self._apply_validation_feedback(validation)
                retry_count += 1

            except Exception as e:
                return f"生成失败: {str(e)}"

        # 添加最终响应到历史
        if final_response:
            self._add_message("assistant", final_response)
            return final_response
        else:
            return response + "\n（达到最大修正次数）"

    def _generate_single_response(self):
        """生成单次响应"""
        response = self.client.chat.completions.create(
            model=self.config["model"]["name"],
            messages=self._build_generation_context(),
            temperature=self.config["model"]["temperature"],
            max_tokens=self.config["model"]["max_tokens"]
        )
        return response.choices[0].message.content

    def _validate_response(self, response):
        """执行响应验证"""
        try:
            # 构建验证请求
            prompt = self.config["validation"]["system_prompt"]
            prompt = prompt.replace(
                "{active_instructions}",
                json.dumps(self.active_instructions, ensure_ascii=False)
            ).replace("{response}", response)

            validation_resp = self.client.chat.completions.create(
                model=self.config["validation"]["model"],
                messages=[{"role": "system", "content": prompt}],
                temperature=self.config["validation"]["temperature"],
                max_tokens=self.config["validation"]["max_tokens"]
            )

            result = json.loads(validation_resp.choices[0].message.content)

            print(validation_resp.choices[0].message.content)
            return {
                "valid": result.get("valid", False),
                "violations": result.get("violations", [])
            }
        except Exception as e:
            print(f"验证失败: {str(e)}")
            return {"valid": True, "violations": []}  # 验证失败视为通过

    def _apply_validation_feedback(self, validation):
        """应用验证反馈到上下文"""
        feedback = "请修正以下问题：\n" + "\n".join(
            [f"- {v['description']}（建议：{v['suggestion']}）"
             for v in validation["violations"]])

        # 保留原始对话但添加系统反馈
        self.conversation_history.append({
            "role": "system",
            "content": feedback
        })

    def _build_generation_context(self):
        """构建生成上下文（自动应用指令）"""
        context = self.conversation_history.copy()

        # 自动附加生效指令
        if self.active_instructions:
            instruction_desc = "必须遵守的指令：\n" + "\n".join(
                [f"- {inst['description']}" for inst in self.active_instructions]
            )
            context.insert(-1, {  # 在最后一条用户输入前插入
                "role": "system",
                "content": instruction_desc
            })

        return context

    def _check_instruction_conflicts(self, user_input):
        """冲突检测主方法"""
        if not self.active_instructions:
            return

        # 准备现有指令描述
        instructions_desc = "\n".join(
            f"{idx + 1}. {inst['name']} ({inst['description']})" for idx, inst in enumerate(self.active_instructions))

        # 构建冲突检测请求
        response = self.client.chat.completions.create(
            model=self.config["instruction_model"]["name"],
            messages=[
                {"role": "system", "content": self.config["conflict_check"]["system_prompt"]
                .replace("{existing_instructions}", instructions_desc)},
                {"role": "user", "content": user_input}
            ],
            temperature=0.1,  # 低随机性确保稳定性
            max_tokens=300
        )

        # 解析并应用冲突解决方案
        try:
            result = json.loads(response.choices[0].message.content)
            for conflict in result.get("conflicts", []):
                self._replace_instruction(
                    conflict["old_name"],
                    conflict["new_instruction"]
                )
        except Exception as e:
            print(f"冲突检测失败: {str(e)}")

    def _replace_instruction(self, old_name, new_instruction):
        """执行指令替换"""
        # 添加创建时间和来源
        full_instruction = {
            **new_instruction,
            "created_at": time.time(),
            "source": "replacement"
        }

        # 查找并替换旧指令
        replaced = False
        for i, inst in enumerate(self.active_instructions):
            if inst["name"] == old_name:
                self.active_instructions[i] = full_instruction
                print(f"指令已更新：{old_name} -> {full_instruction['name']}")
                replaced = True
                break

        if not replaced:
            self.active_instructions.append(full_instruction)
            print(f"新增冲突解决指令：{full_instruction['name']}")

    def _extract_instructions(self, latest_user_input):
        """使用小模型提取用户指令"""
        try:
            # 构建指令识别请求
            response = self.client.chat.completions.create(
                model=self.config["instruction_model"]["name"],
                messages=[
                    {"role": "system", "content": self.config["instruction_model"]["system_prompt"]},
                    {"role": "user", "content": latest_user_input}
                ],
                temperature=self.config["instruction_model"]["temperature"],
                max_tokens=self.config["instruction_model"]["max_tokens"]
            )

            # 解析响应
            result = json.loads(response.choices[0].message.content)
            print(result)
            if "instructions" in result:
                for inst in result["instructions"]:
                    self._add_instruction({
                        **inst,
                        "created_at": time.time(),
                        "source": "user"
                    })

        except json.JSONDecodeError:
            print("指令解析失败：响应不是有效JSON格式")
        except Exception as e:
            print(f"指令提取失败：{str(e)}")

    def _add_instruction(self, instruction):
        """智能添加指令（自动处理同名更新）"""
        instruction = {
            **instruction,
            "created_at": time.time(),
            "source": instruction.get("source", "user")
        }

        # 查找同名指令
        same_name = [i for i, inst in enumerate(self.active_instructions)
                     if inst["name"] == instruction["name"]]

        if same_name:
            # 保留最新指令
            self.active_instructions[same_name[0]] = instruction
            print(f"指令已更新：{instruction['name']}")
        else:
            self.active_instructions.append(instruction)
            print(f"新指令已存储：{instruction['name']}")

    def get_active_instructions(self):
        """获取当前生效的指令"""
        return self.active_instructions.copy()

    def clear_instructions(self):
        self.active_instructions = []

    def _add_message(self, role, content):
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    def get_history(self):
        return self.conversation_history.copy()

    def reset_history(self):
        self.conversation_history = []

