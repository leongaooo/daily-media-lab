# Remotion Editorial 制作方案

Remotion是共享合成出口；新主视觉可来自Blender镜头母版，见 [blender-handoff.md](blender-handoff.md)。完整镜头层绕过旧顶部标题和top244对象舞台，按原1920×1080呈现并仅在y904裁罩，保留公共字幕；不默认暗化、渐变或追加运镜。下方旧组件说明仅对显式图解项目适用。

这是news-to-video共享的视频合成方案。它把文稿转换成一个`daily_editorial`横屏节目，固定1920×1080、24fps和底部字幕轨；镜头拥有自己的构图、文字、图形、图片和动画。字幕和配音是主时间轴，镜头根据字幕语义自由构图，并保留固定底部字幕轨。SRT 仍然独立交付；视频内字幕也可以显式关闭。素材和动画必须避开该区域。

## 运行

本机使用 Node.js 22 和 Remotion 4.0.542。首次准备另一个环境时，在技能外安装固定版本：

```powershell
$install = Join-Path $HOME '.cache/news-to-video/remotion-editorial'
npm.cmd install --prefix $install --no-audit --no-fund '@remotion/cli@4.0.542' 'remotion@4.0.542' 'react@19.3.1' 'react-dom@19.3.1'

$runtime = Get-Content "$HOME/.cache/news-to-video/runtime.json" -Raw | ConvertFrom-Json
& $runtime.python "<repository>/skills/news-to-video/scripts/render.py" "项目.json" --output "成片目录"
```

runtime.json 可以用 remotion_install 指向独立安装目录。渲染器使用现有本地 FFmpeg 合成配音和音乐，不调用 Remotion 云端服务。

## 新制作与项目组件

显式旧图解的[对象舞台v2](object-stage-v2.md)提供连续对象动作及全宽主图；v1显式兼容旧七类构图。editorial.component_dir接入本地Stage.tsx，stage在复制公共模板后复制用户源模块，字幕外壳不被覆盖。修改项目源而不是remotion/src生成目录，源码参与缓存。

## v1项目配置示例

```json
{
  "editorial": {
    "width": 1920,
    "height": 1080,
    "fps": 24,
    "captions": "bottom_rail"
  },
  "scenes": [
    {
      "editorial_kind": "hero",
      "headline": "少量激活，全量可取",
      "visual_direction": "图片建立环境，文字与主体形成非对称构图"
    },
    {
      "editorial_kind": "flow",
      "headline": "按本幕证据配置流程",
      "editorial_nodes": [
        {"title": "核对依赖", "detail": "SDK 与锁文件"},
        {"title": "隔离回归", "detail": "签名与错误分支"},
        {"title": "激活后核验", "detail": "实际交易结果"}
      ]
    },
    {
      "editorial_kind": "chart",
      "data": [{"label": "8 通道随机读", "value": 2000}],
      "unit": "K",
      "data_source": "保留原始测试口径和来源"
    }
  ]
}
```

目前提供hero_scene、timeline、system_map、evidence_board、workbench、comparison、story七类视觉语法，并兼容hero、flow、chart。AI可以自由组合它们，不把组件当成固定栏目模板；story包含2—4个带语义标题的连续shots，必须属于同一个story_world。`motion_plan`中的entrance、emphasis和camera由组件实际消费；不支持的动效字段必须在报告中说明。底部字幕轨固定占用 y=904..1080；镜头内容必须结束在 y=904 之前，字幕按实际语义时间线替换。设置 `captions` 为 `off` 时仍输出 SRT，但视频不烧录字幕。省略 editorial_kind 时由场景模式和视觉要求作有限推断；复杂稿件应由制作代理显式选择。新增镜头不改变声音接口；实际支持字段见可执行视觉契约。

代码生成素材优先于图片：流程节点、箭头、图表、数字、网格、路径、抽象设备和 UI 结构由 Remotion 组件生成。需要环境质感、真实对象或视觉隐喻时，沿用 image_generation 与 generate_images.py，生成结果仍写入项目资产清单后再渲染。不能使用生成图替代事实图表、真实产品或现场证据。

验证重点是构图是否服务文稿、镜头是否有明确变化、文字是否可读、图片是否与语义匹配、来源是否保留、音视频是否完整解码。渲染报告明确记录 layout_contract 为 editorial，报告使用Editorial字幕轨约定；报告会记录 bottom caption rail 的保留范围。



## 数据与本机浏览器约定（2026-11-11）

flow必须提供2—3个editorial_nodes，每个节点包含非空title与可选detail；缺少节点预检报错，不复用示例题材。hero图片默认editorial_image_fit=contain，完整保留图解文字；仅无需精确边缘的场景图可显式使用cover，缩放被图片容器裁切，不扩张到字幕轨。editorial_summary可提供画面摘要，data_source显示本幕来源。场景与字幕使用全局时间取整的共享帧边界，避免多幕累计舍入漂移。

本机已有Chrome/Edge时，可设置NEWS_TO_VIDEO_BROWSER为其可执行文件的绝对路径；配置读取此路径，不必重复下载Headless Shell。未配置仍沿用Remotion默认浏览器策略。该路径是运行环境配置，不是项目素材；交付包不包含浏览器或node_modules。


## 可执行视觉契约 v1（2026-11-14）

以上旧版四组件与纯规划字段的限制由[可执行视觉契约](executable-visuals.md)扩展：新项目使用七类构图、三类素材、palette与字幕绑定shots。导演自由文本仍需翻译到结构化字段，不能宣称文本本身自动执行。旧项目不静默迁移。
