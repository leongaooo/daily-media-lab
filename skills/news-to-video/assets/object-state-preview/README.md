# 对象与状态合成示例

该公开夹具使用 12 秒合成静音作为冻结输入，顺序验证模块位移、链路出现和交付点前移。在光路动作结束帧触发一个合成提示音，底部字幕与动画通过正式渲染入口合成。实际新闻的带声预演使用最终口播的样本窗口。

在 `news-to-video` 根目录，用已配置的渲染 Python 环境执行以下命令。将示例路径替换为媒体工作盘下尚不存在的目录，TEMP／TMP 随该作业配置。

```powershell
python assets/object-state-preview/build.py --work E:/media/synthetic-object-preview
python scripts/render.py E:/media/synthetic-object-preview/project.json --output E:/media/synthetic-object-preview/output
```

比较 0.6／3.0、4.6／7.0、8.6／11.0 秒的画面。检查 `validation.json` 中 288 帧、三个字幕 cue、冻结声逐字节保留和提示音的起始秒数。比较 `remotion/src/data.json`、其中的 `custom/Stage.tsx` 与实际画面。这套数据用于验证生产链连接和动作呈现。
