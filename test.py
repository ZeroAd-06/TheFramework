from data_loader import DataLoader
from batch_processor import BatchProcessor


def main():
    input_path = "InfoBench.json"  # 输入数据集路径
    output_path = "ControlOutput7B.json"  # 输出文件路径

    try:
        # 加载数据
        loader = DataLoader(input_path)
        data = loader.load_data()

        # 处理数据
        processor = BatchProcessor()
        processor.process_dataset(data, output_path)

    except Exception as e:
        print(f"运行失败: {str(e)}")


if __name__ == "__main__":
    main()