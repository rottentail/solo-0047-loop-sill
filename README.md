# 环映台 Loop Sill

环映台用于检查展陈素材首尾接缝。把 Y4M 画面和 PCM WAV 拾音登记为一对，可搜索相近接点、观察波形、跨缝试听，再把指定接缝稿封存为可移交环带。

## 启动

需要 Python 3.11 或更新版本和支持 Web Audio 的现代浏览器。Python 端只用标准库，网页无在线依赖。

```sh
python3 -m loopsill serve --port 8787
```

打开 `http://127.0.0.1:8787`。点击「载入青幕摆灯」试放整帧率素材，或点击「载入双节拍幕」试放 30000/1001 格/秒与 44.1 kHz 双声道组合。测量接缝后可搜索等长候选，再生成预演并跨缝播放。保存一稿后可从历史区打开、封存并下载环带。状态默认保存在 `.loopsill-data`，可用 `--data` 指定其他目录。

## 本地接收与演练

```sh
python3 -m loopsill demo counterbeat ./demo-counterbeat
python3 -m loopsill verify ./loop-example.zip
python3 -m loopsill rehearse ./loop-example.zip ./rehearsal --turns 9
```

`demo` 创建可上传的 `capture.y4m`、`capture.wav` 和建议选区。`verify` 输出核验后的清单。`rehearse` 创建画面 `rehearsal.y4m`、拾音 `rehearsal.wav` 与每圈样本边界 `rehearsal.json`。生成目录须不存在。输入上限、选区、交叠和时钟规则见项目规格。

`python3 -m loopsill walkthrough preview` 运行一次用完即清理的生产演练。其他演练名为 `ingest`、`measure`、`scan`、`save`、`inspect`、`freeze`、`download`、`verify` 和 `rehearse`。

## 接口

`GET /api/captures` 列出已登记素材。登记使用 `POST /api/captures?label=…`，请求体为 4 字节无符号大端画面长度、画面字节、拾音字节，类型为 `application/octet-stream`。演示用 `POST /api/demos/pendulum` 或 `POST /api/demos/counterbeat`。

在 `/api/captures/{id}` 下，`measure` 和 `preview` 接收直接的 `start`、`end`、`overlap`、`offset` JSON 对象。`scan` 接收 `selection`、`radius`、`focus`，优先项为 `balanced`、`picture` 或 `sound`。`waveform` 接收 `selection`、`bins`。`drafts` 接收 `selection` 和 `expected`，首次稿号预期值为 0。`handoffs` 接收待封存的 `revision`；通过 `GET /api/handoffs/{id}` 下载。以 `GET` 读取 `drafts` 和 `handoffs` 列表。`frame/{index}` 读取绝对来源画格的 PNG。`preview/audio` 和 `preview/sheet/{index}` 以四个选区参数查询处理后 WAV 或 PNG 拼页。

独立测试套件延期。合成演练覆盖正常结果及代表性输入错误，服务及离线接收都可在无网络环境运行。
