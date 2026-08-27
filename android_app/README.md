# 猪咪备忘录 Android 原型

这是与 Windows 客户端共享文本分类和 SQLite 存储思路的 PySide6 前台原型。它支持文本/图片分栏、搜索、去重、重新复制与本地持久化。

Android 10 及更高版本只允许当前获得焦点的应用或默认输入法读取剪贴板，因此普通应用无法复刻 Windows 版的后台常驻监听。本原型在应用位于前台时响应剪贴板变化，也提供“读取当前剪贴板”按钮。

## 当前电脑的开发环境

已配置 Windows Android Studio + Ubuntu 24.04 WSL：

- Android Studio：在 Windows 端编辑和管理项目；若日后需要其内置模拟器，可在首次启动时按向导另行安装 Windows 端 SDK。
- WSL：实际运行 PySide6 Android 部署工具，避免 Windows 宿主不受支持的问题。
- WSL Android SDK：API 35、Build Tools 35.0.0、NDK 26.1.10909125、CMake 3.22.1。
- WSL Python 环境：`/home/zhumi/venvs/zhumi-android`，使用 CPython 3.11.16，包含 PySide6、Buildozer、qtpip 和部署依赖。PySide6 Android 部署工具当前要求 Python 3.11 或更低版本。
- aarch64 Android wheels：`/home/zhumi/android-wheels`，适用于绝大多数实体 Android 手机。

双击 `open_android_wsl.bat` 可以进入已定位到项目根目录的 WSL 终端。Windows 中用 Android Studio 打开项目根目录即可编辑代码；保存后的文件会立刻被 WSL 看到。

不生成 APK 的环境预检：

```bash
bash android_app/verify_wsl_environment.sh
```

## 后续构建 APK

1. 安装与目标 PySide6 版本匹配的 Android SDK、NDK。
2. 下载同版本、同架构的 PySide6 与 Shiboken6 Android wheels。
3. 创建项目外的 Python 虚拟环境，并安装 PySide6。
4. 设置 `PYSIDE_ANDROID_WHEEL`、`SHIBOKEN_ANDROID_WHEEL`、`ANDROID_SDK_ROOT`、`ANDROID_NDK_ROOT`。
5. 在仓库根目录运行 `bash android_app/build_apk.sh`。

在本机 WSL 中，以上变量和部署工具路径已经设置完成。之后需要打包时，在 `open_android_wsl.bat` 打开的终端运行：

```bash
bash android_app/build_apk.sh
```

该命令才会生成 APK；本次环境安装没有执行它。

Qt 官方部署工具当前只能在 Linux 或 macOS 主机运行；本项目通过 WSL 提供 Linux 构建主机，Windows 本身不直接执行该工具。当前环境以 `aarch64` 为目标，适合绝大多数实体 Android 手机；若要使用 x86_64 模拟器，需要另行下载与 PySide6 版本匹配的 x86_64 wheels，并调整部署配置。
