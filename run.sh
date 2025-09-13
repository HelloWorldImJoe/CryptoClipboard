#!/bin/bash

# 开发模式启动脚本

echo "🚀 启动 Crypto Clipboard (开发模式)"
echo "=================================="

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: Python 3 未安装"
    exit 1
fi

# 检查是否在项目目录
if [ ! -f "src/main.py" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 检查虚拟环境
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  警告: 建议创建虚拟环境"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate  # macOS/Linux"
    echo "   # 或"
    echo "   venv\\Scripts\\activate    # Windows"
    echo ""
fi

# 尝试安装依赖
echo "📦 检查依赖..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: requirements.txt 文件未找到"
    exit 1
fi

# 安装依赖（忽略错误，某些依赖可能已安装）
echo "🔧 安装/更新依赖..."
pip install -r requirements.txt 2>/dev/null || echo "⚠️  某些依赖可能未安装成功"

# 创建assets目录（如果不存在）
if [ ! -d "assets" ]; then
    echo "📁 创建assets目录..."
    mkdir -p assets
fi

echo ""
echo "🎯 启动应用..."

echo "启动命令行版本..."
echo "使用 Ctrl+C 退出或在交互模式下输入 'quit'"
echo ""
python3 cli_main.py "$@"