# Windows 修复验证记录

## 本次修复

- 共享矢量数据的 Y 轴由 AppKit 向上转换为 Qt 向下；轮盘、预览、落点图标使用同一转换。
- Windows 音效从 QMediaPlayer/MP3 改为 QSoundEffect/PCM WAV，避开用户日志中报错的 FFmpeg 音频重采样路径。
- 默认输出设备切换后重建播放器；静音时不加载音效；加载期间取消或切换信号不会补播旧请求。

## 已执行

- `PYTHONPATH=windows python -m unittest discover -s windows/tests -v`：24 项通过，5 项跳过。
- `python -m compileall -q windows scripts/convert-windows-sounds.py`：通过。
- 九个 WAV：双声道、44.1 kHz、16 位 PCM、有效时长且有非静音采样。
- 八项音频请求测试使用模拟 Qt 设备/加载器，验证加载、取消、切换、音量、无设备和失败重试的控制逻辑；它们不是实际音频播放测试。

## 未执行 / 不应视为通过

- 两项新增 Qt 图标方向回归测试：当前环境未安装 PySide6，安装依赖未成功，按条件跳过。
- 三项 Windows 原生输入测试：Linux 环境按平台跳过。
- Qt GUI 冒烟测试、Windows EXE 构建和实机音频输出。
- 混合 DPI、多屏、全屏应用、托盘、锁屏和睡眠恢复。

本地 Windows 构建脚本会运行 Qt 图标方向测试及 GUI 冒烟检查。请在用户报告问题的电脑上进一步确认：问号圆点位于下方，九种信号都能出声，静音有效，切换耳机后可以继续播放。未声称 Windows 实机验证通过。
