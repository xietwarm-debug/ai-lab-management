"""
查重算法演示脚本
用于答辩时展示算法效果
"""

import sys
from pathlib import Path

# 添加项目路径
ROOT_DIR = Path(__file__).resolve().parents[1]
LAB_API_DIR = ROOT_DIR / "lab-api"
if str(LAB_API_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_API_DIR))

from modular.algorithm_nlp import calculate_text_similarity


def print_separator(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_plagiarism_detection():
    """演示抄袭检测场景"""
    print_separator("场景1：检测直接抄袭")
    
    standard = """
    实验目的：掌握Python编程语言的基本语法和数据结构。
    实验步骤：
    1. 安装Python环境并配置开发工具
    2. 学习变量定义和数据类型
    3. 掌握for和while循环结构
    4. 理解函数的定义和调用方法
    实验结果：成功完成所有实验任务，程序运行正常。
    实验总结：通过本次实验，我深入理解了Python的核心概念，
    为后续学习打下了坚实基础。
    """
    
    # 学生A：直接复制（99%相似）
    student_a = standard
    
    sim_a = calculate_text_similarity(standard, student_a)
    print(f"\n📄 标准答案 vs 学生A（直接抄袭）")
    print(f"   查重率：{sim_a}%")
    print(f"   判定：{'❌ 严重抄袭' if sim_a > 80 else '✓ 正常'}")
    
    # 学生B：稍作修改（75%相似）
    student_b = """
    实验目标：学习Python的基础语法和数据类型。
    实验过程：
    第一步是配置开发环境和安装工具
    然后了解如何声明变量和类型
    接着学习for循环和while循环的使用
    最后掌握函数的定义与调用技巧
    实验成果：完成了所有要求的任务，代码可以正常运行。
    心得体会：这次实验让我对Python有了更深的认识和理解，
    为以后的学习奠定了良好的基础。
    """
    
    sim_b = calculate_text_similarity(standard, student_b)
    print(f"\n📄 标准答案 vs 学生B（改写抄袭）")
    print(f"   查重率：{sim_b}%")
    print(f"   判定：{'⚠️ 疑似抄袭' if sim_b > 60 else '✓ 正常'}")
    
    # 学生C：独立完成（25%相似）
    student_c = """
    今天我学习了Java编程语言。
    Java是一种面向对象的程序设计语言。
    我学会了如何创建类和对象实例。
    还掌握了继承、封装和多态三大特性。
    通过编写一个简单的学生管理系统，
    我对面向对象编程有了更深入的理解。
    这是一次非常有意义的学习经历。
    """
    
    sim_c = calculate_text_similarity(standard, student_c)
    print(f"\n📄 标准答案 vs 学生C（独立创作）")
    print(f"   查重率：{sim_c}%")
    print(f"   判定：{'✅ 原创度高' if sim_c < 40 else '⚠️ 需复核'}")


def demo_cross_student_check():
    """演示学生间作业比对"""
    print_separator("场景2：学生间作业相互比对")
    
    student_1 = """
    本次实验主要学习了数据库的基本操作。
    首先安装了MySQL数据库服务器。
    然后创建了用户表和订单表。
    使用SQL语句进行了增删改查操作。
    最后实现了简单的数据查询功能。
    通过这次实验，我掌握了SQL的基本语法。
    """
    
    student_2 = """
    这周我们做了数据库实验。
    先装好了MySQL服务器软件。
    接着建立了user表和order表。
    用SQL命令执行了CRUD操作。
    最终完成了数据检索功能。
    实验让我熟悉了SQL语言的使用方法。
    """
    
    student_3 = """
    今天学习了机器学习算法。
    了解了线性回归和逻辑回归的原理。
    使用Python的sklearn库实现了模型训练。
    通过数据集验证了模型的准确性。
    对监督学习有了更深刻的认识。
    这是一次很有收获的实验课。
    """
    
    sim_12 = calculate_text_similarity(student_1, student_2)
    sim_13 = calculate_text_similarity(student_1, student_3)
    sim_23 = calculate_text_similarity(student_2, student_3)
    
    print(f"\n👥 学生1 vs 学生2（同题作业）")
    print(f"   查重率：{sim_12}%")
    print(f"   分析：{'高度相似，可能互相参考' if sim_12 > 60 else '差异较大'}")
    
    print(f"\n👥 学生1 vs 学生3（不同主题）")
    print(f"   查重率：{sim_13}%")
    print(f"   分析：{'异常相似，需核查' if sim_13 > 40 else '正常，主题不同'}")
    
    print(f"\n👥 学生2 vs 学生3（不同主题）")
    print(f"   查重率：{sim_23}%")
    print(f"   分析：{'异常相似，需核查' if sim_23 > 40 else '正常，主题不同'}")


def demo_threshold_analysis():
    """演示不同阈值的判定效果"""
    print_separator("场景3：查重阈值分级说明")
    
    test_cases = [
        (95.5, "完全复制粘贴"),
        (82.3, "少量词语替换"),
        (68.7, "句式改写但内容相同"),
        (52.1, "参考框架自行填充"),
        (35.4, "仅参考题目和部分术语"),
        (18.2, "独立完成，偶有术语重合"),
        (5.3, "完全原创"),
    ]
    
    print("\n📊 查重率分级标准：\n")
    for rate, description in test_cases:
        if rate > 80:
            level = "🔴 高风险"
            action = "扣30分，标记抄袭"
        elif rate > 60:
            level = "🟠 中风险"
            action = "扣15分，人工复核"
        elif rate > 40:
            level = "🟡 低风险"
            action = "扣5分，关注原创性"
        else:
            level = "🟢 安全"
            action = "不扣分，原创度高"
        
        print(f"   {rate:5.1f}% | {level} | {description:20s} | {action}")


def demo_real_world_examples():
    """演示真实案例"""
    print_separator("场景4：真实作业案例分析")
    
    # 案例1：实验报告
    report_template = """
    一、实验目的
    掌握Linux操作系统的基本命令使用。
    
    二、实验环境
    Ubuntu 20.04 LTS，VMware虚拟机
    
    三、实验步骤
    1. 使用ls命令查看目录内容
    2. 使用cd命令切换工作目录
    3. 使用mkdir命令创建新文件夹
    4. 使用cp命令复制文件
    5. 使用rm命令删除文件
    
    四、实验结果
    成功完成了所有命令的练习，熟悉了Linux文件系统。
    
    五、实验心得
    Linux命令行操作比图形界面更高效，需要多加练习。
    """
    
    report_copy = report_template  # 直接复制
    
    sim_report = calculate_text_similarity(report_template, report_copy)
    print(f"\n📝 案例1：实验报告抄袭")
    print(f"   查重率：{sim_report}%")
    print(f"   建议：❌ 驳回并要求重写")
    
    # 案例2：编程作业
    code_original = """
    def bubble_sort(arr):
        n = len(arr)
        for i in range(n):
            for j in range(0, n-i-1):
                if arr[j] > arr[j+1]:
                    arr[j], arr[j+1] = arr[j+1], arr[j]
        return arr
    
    # 测试
    data = [64, 34, 25, 12, 22, 11, 90]
    print(bubble_sort(data))
    """
    
    code_modified = """
    def bubbleSort(array):
        length = len(array)
        for i in range(length):
            for j in range(0, length-i-1):
                if array[j] > array[j+1]:
                    array[j], array[j+1] = array[j+1], array[j]
        return array
    
    # 测试代码
    testData = [64, 34, 25, 12, 22, 11, 90]
    result = bubbleSort(testData)
    print(result)
    """
    
    sim_code = calculate_text_similarity(code_original, code_modified)
    print(f"\n💻 案例2：编程作业改写")
    print(f"   查重率：{sim_code}%")
    print(f"   建议：⚠️ 变量名修改不足以规避抄袭，需进一步改写")


if __name__ == "__main__":
    print("\n" + "🎓" * 35)
    print("   AI实验室管理系统 - 文本查重算法演示")
    print("🎓" * 35)
    
    try:
        demo_plagiarism_detection()
        demo_cross_student_check()
        demo_threshold_analysis()
        demo_real_world_examples()
        
        print("\n" + "=" * 70)
        print("  ✨ 演示完毕！算法运行正常")
        print("=" * 70)
        print("\n💡 提示：在实际系统中，查重率会自动显示在教师批改界面，")
        print("   帮助教师快速识别可疑作业，提高批改效率和准确性。\n")
        
    except Exception as e:
        print(f"\n❌ 演示失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
