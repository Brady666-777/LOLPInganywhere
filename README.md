# LoLPing · Windows 桌面信号

将 [LoLPing-Mac](https://github.com/AllenTHT/LoLPing-Mac) 的桌面 Ping 交互移植到 **Windows 10/11 x64**。Windows 实现位于 `windows/`，使用 Python / PySide6、Win32 全局输入监听和 Qt 透明悬浮窗；原 Swift/macOS 源码仍然保留。

> 当前为 Windows 移植初版。尚未完成 Windows 实机验收，也未发布预编译安装包。请使用下方自动构建流程生成程序；自动测试通过不代表全屏游戏和多显示器已实测。

## 功能

- 按住 **Ctrl + Alt + Shift** 约 0.18 秒呼出八向轮盘，中央是普通信号；松开任意一键发送。
- 九种信号、原仓库矢量图标和由原 MP3 转换的 PCM WAV 音效；Esc / 右键取消，其他按键、鼠标点击和滚轮也会取消。
- 信号显示在最初呼出的位置，轮盘在屏幕边缘自动向内移动。下一次触发前必须完全松开组合键。
- 托盘开关、窗口内试用、三组快捷键、音量与 75%–150% 大小设置；首次运行默认关闭。
- 设置保存至 `%LOCALAPPDATA%\LoLPing\settings.json`。不添加开机启动项，不联网同步，不向游戏注入输入。

这是本机桌面效果工具，**不会给英雄联盟队友发送信号**。

## 获得 Windows 程序

将本次移植代码放入仓库后，打开 **Actions → Build Windows**，查看分支推送触发的构建。工作流进入默认分支后也可通过 **Run workflow** 手动运行。

成功后下载 **Artifacts → LoLPing-Windows-x64**，解开下载的压缩包，再解开其中的 `LoLPing-Windows-x64.zip`。保留整个 `LoLPing` 文件夹，双击 `LoLPing.exe`；不要只复制 EXE，它依赖同目录的 `_internal` 文件夹。用户电脑不需要安装 Python。

本地运行及打包、已知限制、实机验收清单见 **[Windows 使用与开发说明](windows/README.md)**。

## 开发检查

纯逻辑测试不依赖 GUI，可以在 Linux/macOS/Windows 上运行：

```sh
PYTHONPATH=windows python -m unittest discover -s windows/tests -v
```

Windows 构建脚本额外运行原生输入监听检查、界面渲染检查和打包后素材检查。见 [验证记录](windows/VERIFICATION.md)。

## 原项目与素材

[macOS 原使用说明](README-macOS.md) · [素材来源清单](Resources/asset-sources.json)

图标与音效继续使用原仓库资源；Windows 动画为重新实现，未声称与原游戏或 macOS 版本逐帧一致。游戏素材归 Riot Games 所有，本项目是独立的个人桌面工具，非 Riot 官方产品。分发时请保留素材来源说明，并遵守各上游素材及 PySide6/Qt 的许可要求。
