# 在本机调试 LoLPing

这个包是完整的可构建源码，包含图标方向和 WAV 音效修复、素材、测试、构建脚本，以及 VS Code 调试配置。它不包含预编译 EXE、Python 虚拟环境或 Git 历史。Windows 实机显示及音频效果仍需在本机验证。

## 首次准备

1. 安装 Python 3.12 x64 和 VS Code。
2. 解压后将包内 `LoLPing-Win` 文件夹放到例如 `D:\projects\LoLPing-Win`。如果该路径已有项目或自己的改动，请先放到另一个新目录。
3. 在 VS Code 选择「文件 → 打开文件夹」，打开包含 `windows`、`Resources` 和 `.vscode` 的那层目录。
4. 安装工作区推荐的 Microsoft Python、Python Debugger 扩展。
5. 在 VS Code 的 PowerShell 终端执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r windows\requirements.txt
```

这些命令不需要激活虚拟环境，也不需要更改系统执行策略。首次安装依赖需要联网，日常运行使用本地素材。

## 调试和运行

先从系统托盘彻底退出旧的 LoLPing 实例，否则单实例检查会阻止调试程序启动。

按 F5，选择 **LoLPing: 调试 Windows 程序**。可以直接在 `.py` 文件左侧设置断点；程序输出和错误会显示在集成终端。修改 Python 文件后，停止当前调试并重新启动即可，不必每次打包 EXE。

不使用 VS Code 时，在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe windows\main.py
```

调试普通界面和音效时，可以关闭「启用全局 Ping」，通过九个试用按钮触发。不要在 `win32.py` 的低级输入钩子回调内长时间暂停，Windows 可能因超时移除钩子；手势逻辑优先用「调试单元测试」配置打断点。

## 测试

F5 的另外两个配置：

- **LoLPing: 调试单元测试**：运行所有测试，可在手势逻辑和测试代码中打断点。
- **LoLPing: 检查界面和素材**：绘制轮盘和动画、检查资源及取消行为，然后自动退出；不测试实际声音。

命令行等效操作：

```powershell
$env:PYTHONPATH = "$PWD\windows"
.\.venv\Scripts\python.exe -m unittest discover -s windows\tests -v
.\.venv\Scripts\python.exe windows\main.py --smoke-test
```

实际验证时，请检查问号圆点在下方、九种信号能出声、关闭开关立即停止、切换默认耳机后可再次播放。音频请求单元测试使用模拟设备，不代替实际听音测试。

## 常用文件

- `windows/lolping/visuals.py`：图标、轮盘、落点动画。
- `windows/lolping/audio.py`：WAV 播放及设备切换。
- `windows/lolping/core.py`：手势状态机和方向选择。
- `windows/lolping/win32.py`：Windows 输入钩子及显示器信息。
- `windows/lolping/app.py`：设置窗口、托盘和事件调度。

设置保存在 `%LOCALAPPDATA%\LoLPing\settings.json`，解压新项目不会清除它，旧的启用状态可能在启动时恢复。

## 手动提交到已有仓库

如果已经克隆了自己的仓库，可先备份本地改动，再把包内内容复制到仓库根目录，保留原来的 `.git`。包含隐藏的 `.github`、`.vscode` 和 `.gitignore`。检查 `git diff` 后提交自己的修改即可；`.venv` 不应提交。

EXE 打包方法见 `windows/README.md`。修改源码不会自动更新已有 EXE。
