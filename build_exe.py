import PyInstaller.__main__
import os
import sys
import shutil
import time

def clean_build_files():
    """清理build目录和临时文件"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 要清理的目录和文件
    cleanup_items = [
        os.path.join(current_dir, "build"),
        os.path.join(current_dir, "*.spec"),
        os.path.join(current_dir, "__pycache__"),
    ]
    
    print("\n正在清理临时文件...")
    
    for item in cleanup_items:
        if "*" in item:
            # 处理通配符文件
            import glob
            for file_path in glob.glob(item):
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"  ✓ 删除文件: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"  ✗ 删除文件失败 {os.path.basename(file_path)}: {e}")
        else:
            # 处理目录
            if os.path.exists(item):
                try:
                    if os.path.isdir(item):
                        shutil.rmtree(item)
                        print(f"  ✓ 删除目录: {os.path.basename(item)}")
                    elif os.path.isfile(item):
                        os.remove(item)
                        print(f"  ✓ 删除文件: {os.path.basename(item)}")
                except Exception as e:
                    print(f"  ✗ 删除失败 {os.path.basename(item)}: {e}")

def get_file_size_mb(file_path):
    """获取文件大小（MB）"""
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
    return 0

def build_exe():
    """构建exe文件"""
    
    # 获取当前脚本目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 源文件路径 - 修正为正确的文件名
    main_script = os.path.join(current_dir, "image_to_pdf1.4.2.py")  # 脚本路径
    icon_file = os.path.join(current_dir, "漫画.ico")              # 图标路径
    version_file = os.path.join(current_dir, "version_info.txt")
    
    # 检查文件是否存在
    if not os.path.exists(main_script):
        print(f"错误：找不到源文件 {main_script}")
        print("请确保 image_to_pdf4.0.py 文件存在")
        return False
        
    if not os.path.exists(icon_file):
        print(f"警告：找不到图标文件 {icon_file}")
        icon_file = None
    
    if not os.path.exists(version_file):
        print(f"警告：找不到版本信息文件 {version_file}")
        version_file = None
    
    # PyInstaller参数
    args = [
        main_script,                    # 主脚本文件
        "--onefile",                    # 打包成单个exe文件
        "--console",                    # 显示控制台窗口（改为console，因为需要用户交互）
        "--name=图片转PDF工具",    # 输出文件名
        "--clean",                      # 清理临时文件
        "--noconfirm",                  # 不询问覆盖
        "--optimize=2",                 # 优化级别
        "--strip",                      # 去除调试信息
        "--exclude-module=tkinter",     # 排除不需要的模块
        "--exclude-module=matplotlib",  # 排除不需要的模块
        "--exclude-module=numpy",       # 排除不需要的模块
        "--exclude-module=pandas",      # 排除不需要的模块
        "--exclude-module=scipy"，       # 排除不需要的模块
        "--exclude-module=IPython",     # 排除不需要的模块
        "--exclude-module=jupyter",     # 排除不需要的模块
        "--exclude-module=setuptools",  # 排除不需要的模块
        "--exclude-module=distutils",   # 排除不需要的模块
    ]
    
    # 添加图标参数
    if icon_file:
        args.extend(["--icon", icon_file])
    
    # 添加版本信息
    if version_file:
        args.extend(["--version-file", version_file])
    
    print("=" * 50)
    print("    图片转PDF工具 - 自动打包脚本")
    print("=" * 50)
    print(f"源文件: {os.path.basename(main_script)}")
    if icon_file:
        print(f"图标文件: {os.path.basename(icon_file)}")
    if version_file:
        print(f"版本信息: {os.path.basename(version_file)}")
    print("=" * 50)
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        print("正在执行打包...")
        # 执行打包
        PyInstaller.__main__.run(args)
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        # 检查生成的exe文件
        exe_path = os.path.join(current_dir, "dist", "图片转PDF工具.exe")
        if os.path.exists(exe_path):
            file_size = get_file_size_mb(exe_path)
            print("\n" + "=" * 50)
            print("    打包成功！")
            print("=" * 50)
            print(f"✓ 生成文件: {os.path.basename(exe_path)}")
            print(f"✓ 文件大小: {file_size} MB")
            print(f"✓ 文件位置: dist/")
            print(f"✓ 打包耗时: {elapsed_time:.1f} 秒")
            print("=" * 50)
            
            # 自动清理build文件
            clean_build_files()
            
            print("\n✅ 所有操作完成！")
            return True
        else:
            print("\n❌ 打包完成但未找到生成的exe文件")
            return False
            
    except Exception as e:
        print(f"\n❌ 打包失败: {e}")
        return False

def check_dependencies():
    """检查依赖库"""
    print("正在检查依赖库...")
    
    missing_libs = []
    
    # 检查PyInstaller
    try:
        import PyInstaller
        print(f"✓ PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        missing_libs.append("pyinstaller")
    
    # 检查其他必要库
    required_libs = {
        "PIL": "Pillow",
        "tqdm": "tqdm"
    }
    
    for module_name, package_name in required_libs.items():
        try:
            __import__(module_name)
            print(f"✓ {package_name}: 已安装")
        except ImportError:
            missing_libs.append(package_name)
    
    if missing_libs:
        print("\n❌ 缺少以下依赖库:")
        for lib in missing_libs:
            print(f"   - {lib}")
        print("\n请运行以下命令安装:")
        print(f"pip install {' '.join(missing_libs)}")
        return False
    
    print("✅ 所有依赖库检查通过")
    return True

if __name__ == "__main__":
    print("图片转PDF工具 - 打包脚本 v2.0")
    print("功能：自动打包并清理临时文件\n")
    
    # 检查依赖
    if not check_dependencies():
        input("\n按Enter键退出...")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    
    # 执行打包
    success = build_exe()
    
    if success:
        print("\n🎉 打包成功！")
        print("💡 提示：")
        print("   - exe文件位于 dist/ 目录")
        print("   - 可以直接分发使用")
        print("   - 首次运行可能需要几秒钟启动时间")
        print("   - 临时文件已自动清理")
    else:
        print("\n💥 打包失败！")
        print("💡 建议：")
        print("   - 检查源文件是否存在")
        print("   - 确认所有依赖库已安装")
        print("   - 查看上方的错误信息")
    
    input("\n按Enter键退出...")
