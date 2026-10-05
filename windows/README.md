# LoLPing Windows

目标环境：Windows 10/11 x64。Windows ARM64、独占全屏游戏和安全桌面尚不支持或未验证。当前为待实机验收的移植初版。

## 使用

1. 解压整个构建产物，运行 `LoLPing.exe`。首次运行默认关闭全局监听，可以先点击九种信号试用。
2. 勾选「启用全局 Ping」。按住 **Ctrl + Alt + Shift** 约 0.18 秒，移动鼠标选择，松开其中任意一键发送。
3. 不移动鼠标发送普通信号；Esc / 右键取消。其他普通按键、额外修饰键、鼠标点击和滚轮取消手势，并放行原输入。下一次触发前请松开全部组合键。
4. 关闭窗口会留在系统托盘，点击托盘图标重新打开；托盘菜单可暂停或退出。没有系统托盘时，关闭窗口会退出。
5. 关闭总开关立即移除输入监听、取消轮盘、动画和声音。「退出软件」保留启用偏好，下次启动恢复。

本程序只绘制本机桌面效果，不向游戏发 Ping，不读取游戏进程，不记录输入内容。无需 macOS 的辅助功能权限，也不要求以管理员身份启动。

快捷键可选 `Ctrl + Alt + Shift`、`Ctrl + Alt + Win`、`Ctrl + Shift + Win`。修饰键本身仍传递给其他应用，因此可能与 Windows 输入法切换、开始菜单及应用快捷键冲突；按实际环境选择组合键。

设置保存在 `%LOCALAPPDATA%\LoLPing\settings.json`，损坏设置会回退默认值。不写注册表，不创建登录启动项。再次启动时若已有实例，会提示从托盘打开。

## 从源码运行

安装 **Python 3.12 x64**。在仓库根目录的 PowerShell 运行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r windows\requirements.txt
.\.venv\Scripts\python.exe windows\main.py
```

首次安装依赖需要网络，运行程序使用离线打包素材。无需安装 Swift 或 Xcode。

## 打包为 EXE

仍在仓库根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -Python .\.venv\Scripts\python.exe
```

该命令的执行策略仅作用于此次 PowerShell 进程。脚本依次检查 Windows x64 环境、单元测试、GUI 绘制、PyInstaller 打包和打包后冒烟测试，任何检查失败即停止。输出：

```text
dist/LoLPing/LoLPing.exe
dist/LoLPing/_internal/...
dist/LoLPing-Windows-x64.zip
```

完整文件夹包含 Qt、Python 运行时和资源，目标电脑不必安装 Python。当前构建不含代码签名或安装向导。

仓库的 `.github/workflows/windows.yml` 在 Windows runner 上执行相同步骤并上传 ZIP，不自动发布 Release。

## 开发与验收

```powershell
$env:PYTHONPATH = "$PWD\windows"
.\.venv\Scripts\python.exe -m unittest discover -s windows\tests -v
.\.venv\Scripts\python.exe windows\main.py --smoke-test
```

`--smoke-test` 不安装全局监听、不播放音效、不读写用户设置：使用实际矢量素材绘制 27 个轮盘状态和 108 个动画帧，检查预览取消与资源路径，然后退出。可设置 `LOLPING_SMOKE_OUTPUT` 指定主窗口截图路径。原生测试会短暂安装再移除 Win32 输入监听，不注入键鼠事件。

验收前请逐项实测：

- 九种信号位置与音效（问号圆点应在下方）；音量 0/55/100 和大小 75/100/150%。
- 短按不触发、六种松键顺序只发送一次、重复按下一键不再触发、松开全部后恢复。
- Esc、右键、滚轮、普通字母、第四个修饰键取消；已有拖动/按住其他键时不呼出；原快捷键仍可使用。
- 启用时已按住修饰键、关闭时正在呼出、切换窗口、显示器拔插、锁屏/解锁、睡眠/恢复。
- 主屏与左侧/上方负坐标显示器、100/150/200% 混合 DPI；边缘轮盘向内移动但落点保持原位置。
- 关闭主窗后托盘继续工作；退出后输入监听与音效消失；再次运行不会产生第二个实例。
- 普通窗口及无边框全屏。独占全屏、UAC 安全桌面、管理员应用及反作弊保护画面可能无法覆盖或接收输入；本版本不保证这些场景。

Win32 低级钩子把绘图和音效排入 Qt 事件队列，避免在系统输入回调中执行耗时渲染。Windows 仍可能在应用严重卡顿后移除低级钩子；如果停止响应，可关闭再开启总开关恢复。

## 文件结构

- `lolping/core.py`：纯手势状态机和八向几何，Windows 屏幕坐标向下增长。
- `lolping/win32.py`：64 位安全的 ctypes 声明、输入监听、显示器坐标和单实例互斥锁。
- `lolping/visuals.py`：矢量轮盘、透明点击穿透窗口、动画和试用区。
- `lolping/app.py`：托盘、设置、计时器和窗口控制。
- `lolping/audio.py`：QSoundEffect PCM WAV 播放、默认设备变化和延迟加载取消。
- `lolping/settings.py`：配置校验与原子写入。

原 Swift 源码位于 `Sources/`。Windows 复用资源与交互逻辑，不依赖 AppKit，也不尝试直接运行 macOS 二进制文件。

## 图标方向与无声问题修复

共享矢量数据以左下角为原点；Windows 读取时转换为 Qt 的左上角坐标，只翻转图标轮廓。轮盘、中心图标、窗口预览和落点效果共用该转换，文字和扇区方向不变。

Windows 版现在播放 `Resources/SoundsWav/` 的 44.1 kHz、16 位、双声道 PCM WAV，通过 `QSoundEffect` 播放短音效。原先 `QMediaPlayer` 的 MP3/FFmpeg 播放路径已移除，以避开用户日志中的 `Output channel layout "" is invalid or unsupported` 错误。切换默认音频设备后释放旧播放器，下次 Ping 使用新的默认设备；没有输出设备时在窗口底部显示提示。这个修改仍需在报告问题的 Windows 电脑上确认实际出声。

原 MP3 留在 `Resources/Sounds/` 供 macOS 使用。WAV 已随源码提供，正常运行和打包不需要 FFmpeg。维护素材时才需安装 FFmpeg 并运行 `python scripts/convert-windows-sounds.py` 重新生成 WAV。

应用修复文件时先从托盘彻底退出 LoLPing，再覆盖同名文件，并复制新增的 `windows/lolping/audio.py` 和整个 `Resources/SoundsWav/` 文件夹。如果运行的是旧 EXE，必须重新打包；只修改源码不会更新旧 EXE。
