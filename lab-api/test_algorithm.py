"""
文本相似度算法测试脚本
用于验证TF-IDF查重功能是否正常工作
"""

import sys
from pathlib import Path

# 添加项目路径
ROOT_DIR = Path(__file__).resolve().parents[1]
LAB_API_DIR = ROOT_DIR / "lab-api"
if str(LAB_API_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_API_DIR))

from modular.algorithm_nlp import calculate_text_similarity, calculate_multi_text_similarity


def test_basic_similarity():
    """测试基本相似度计算"""
    print("=" * 60)
    print("测试1：基本相似度计算")
    print("=" * 60)
    
    text1 = "这是一个测试文本，用于验证算法的正确性"
    text2 = "这是一个测试文本，用于验证算法的正确性"
    
    similarity = calculate_text_similarity(text1, text2)
    print(f"完全相同文本的相似度：{similarity}%")
    assert similarity == 100.0, f"期望100%，实际{similarity}%"
    print("✓ 通过\n")
    
    text3 = "完全不同的内容，没有任何关系"
    similarity2 = calculate_text_similarity(text1, text3)
    print(f"完全不同文本的相似度：{similarity2}%")
    print("✓ 通过\n")


def test_homework_scenario():
    """模拟作业查重场景"""
    print("=" * 60)
    print("测试2：作业查重场景")
    print("=" * 60)
    
    # 标准答案
    standard_answer = """
    实验目的：掌握Python编程语言的基本语法和数据结构。
    实验步骤：
    1. 安装Python环境
    2. 学习变量定义
    3. 掌握循环结构
    4. 理解函数调用
    实验结果：成功完成所有实验任务，程序运行正常。
    实验总结：通过本次实验，我深入理解了Python的核心概念。
    """
    
    # 学生A的作业（高度相似）
    student_a = """
    实验目的：掌握Python编程语言的基本语法和数据结构。
    实验步骤：
    1. 安装Python环境
    2. 学习变量定义
    3. 掌握循环结构
    4. 理解函数调用
    实验结果：成功完成所有实验任务，程序运行正常。
    实验总结：通过本次实验，我深入理解了Python的核心概念。
    """
    
    # 学生B的作业（中等相似）
    student_b = """
    实验目标：学习Python的基础语法和数据类型。
    实验过程：
    第一步是配置开发环境
    然后了解如何声明变量
    接着学习for和while循环
    最后掌握函数的使用方法
    实验成果：完成了所有要求的任务，代码可以正常运行。
    心得体会：这次实验让我对Python有了更深的认识。
    """
    
    # 学生C的作业（低相似）
    student_c = """
    今天学习了Java编程语言。
    Java是一种面向对象的编程语言。
    我学会了如何创建类和对象。
    还掌握了继承和多态的概念。
    这是一次很有意义的学习经历。
    """
    
    sim_a = calculate_text_similarity(standard_answer, student_a)
    sim_b = calculate_text_similarity(standard_answer, student_b)
    sim_c = calculate_text_similarity(standard_answer, student_c)
    
    print(f"学生A（抄袭）与标准答案的相似度：{sim_a}%")
    print(f"学生B（参考）与标准答案的相似度：{sim_b}%")
    print(f"学生C（原创）与标准答案的相似度：{sim_c}%")
    
    assert sim_a > sim_b > sim_c, "相似度排序不正确"
    print("✓ 通过\n")


def test_multi_comparison():
    """测试批量比对功能"""
    print("=" * 60)
    print("测试3：批量比对功能")
    print("=" * 60)
    
    reference = "人工智能是计算机科学的一个重要分支"
    candidates = [
        "人工智能是计算机科学的一个重要分支",  # 100%
        "机器学习是人工智能的一个子领域",  # 中等
        "今天天气真好",  # 很低
    ]
    
    results = calculate_multi_text_similarity(reference, candidates)
    
    print("批量比对结果：")
    for result in results:
        print(f"  索引 {result['text_index']}: 相似度 {result['similarity']}%")
    
    assert results[0]['similarity'] >= results[1]['similarity'], "排序错误"
    print("✓ 通过\n")


def test_edge_cases():
    """测试边界情况"""
    print("=" * 60)
    print("测试4：边界情况")
    print("=" * 60)
    
    # 空文本
    sim1 = calculate_text_similarity("", "测试")
    print(f"空文本相似度：{sim1}%")
    assert sim1 == 0.0
    
    # None值
    sim2 = calculate_text_similarity(None, "测试")
    print(f"None值相似度：{sim2}%")
    assert sim2 == 0.0
    
    # 极短文本
    sim3 = calculate_text_similarity("a", "b")
    print(f"极短文本相似度：{sim3}%")
    
    print("✓ 通过\n")


if __name__ == "__main__":
    try:
        test_basic_similarity()
        test_homework_scenario()
        test_multi_comparison()
        test_edge_cases()
        
        print("=" * 60)
        print("🎉 所有测试通过！算法模块工作正常")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
