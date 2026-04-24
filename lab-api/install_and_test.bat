@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   AI实验室管理系统 - 查重算法功能
echo ========================================
echo.

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)
echo ✅ Python环境正常

echo.
echo [2/3] 安装依赖包...
pip install jieba==0.42.1 scikit-learn==1.3.2 -q
if errorlevel 1 (
    echo ❌ 错误: 依赖安装失败
    pause
    exit /b 1
)
echo ✅ 依赖安装完成

echo.
echo [3/3] 运行测试...
python test_algorithm.py
if errorlevel 1 (
    echo.
    echo ❌ 测试失败，请检查错误信息
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ✨ 部署成功！可以开始使用了
echo ========================================
echo.
echo 下一步:
echo 1. 启动后端: python app.py
echo 2. 查看演示: python demo_plagiarism.py
echo 3. 阅读文档: 查看 ALGORITHM_README.md
echo.
pause
