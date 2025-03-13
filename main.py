from chat_manager import ChatManager


def main():
    print("初始化聊天机器人...")
    chat = ChatManager()
    print("输入 'exit' 退出对话")
    print("输入 'reset' 重置对话历史\n")

    while True:
        try:
            user_input = input("你: ")
            if user_input.lower() == "exit":
                break
            if user_input.lower() == "reset":
                chat.reset_history()
                print("系统: 对话历史已重置\n")
                continue
            if user_input.lower() == "show_instructions":
                print("\n当前生效指令：")
                for idx, inst in enumerate(chat.get_active_instructions(), 1):
                    print(f"{idx}. [{inst['name']}] {inst['description']}")
                print()
                continue

            response = chat.generate_response(user_input)
            print(f"助手: {response}\n")

        except KeyboardInterrupt:
            print("\n对话已终止")
            break
        except Exception as e:
            print(f"发生错误: {str(e)}")
            break


if __name__ == "__main__":
    main()