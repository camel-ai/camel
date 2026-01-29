# Navi-Bench x Browser Skills: Evaluation + Skill Mining Design

目标：把 `navi-bench`（真实网站任务 + 可编程 evaluator）接入 `examples/toolkits/browser_skills_example` 的 Browser Skills 框架，形成与 WebVoyager 相同的闭环：

1) 跑一个 task case（Browser Agent with Skill）  
2) verify 一次（用 Navi-Bench evaluator 打分）  
3) 成功：从本次 session 的轨迹里提取 skill 入库  
4) 失败：按规则重试（每 task 最多 5 次；每网站最多 100 次）  

本文是“可落地的工程方案”，目标是 **最小改动复用现有 WebVoyager runner/SkillsAgent/skill_extractor**，同时满足 Navi-Bench evaluator 的“在线/页面态验证”需求。

---

## 0. 现有基线（需要复用/保持一致的能力）

Browser Skills 框架的关键链路（已存在）：

- 执行器：`examples/toolkits/browser_skills_example/skill_agent.py`（`SkillsAgent`）
  - LLM 通过 `HybridBrowserToolkit` 工具做浏览器交互
  - 如存在 skills，则把每个 skill 包装成 `subtask_<id>(...)` 工具（优先调用）
- 技能重放：`examples/toolkits/browser_skills_example/action_replayer.py`
  - 基于 aria-label 重定位 ref；失败时可调用“恢复用 ChatAgent”
- 轨迹归档与时间线：`skill_agent.py:save_communication_log()` + `analyze_session.py`
  - 生成 `complete_browser_log.log` / `agent_communication_log.json` / `action_timeline.json`
- 成功后技能抽取：`examples/toolkits/browser_skills_example/subtask_extractor.py`
  - 仅从 `action_timeline.json` 的连续 `individual_action` 切段
  - 用 LLM 识别可复用子流程，写入 `skills_store/<website>/NNN-*/SKILL.md + actions.json`
- WebVoyager runner：`examples/toolkits/browser_skills_example/run_webvoyager_tasks.py`
  - 任务循环 + 重试 + verify + 成功后抽取
  - 有 per-task 重试与 per-website attempt cap 的雏形（可复用策略）

Navi-Bench 的关键链路（已存在于本 repo 的 `navi-bench/` 子目录）：

- 数据行 schema：`navi-bench/navi_bench/base.py:DatasetItem`
  - `task_generation_config_json` 是 Hydra 风格 `_target_` 配置
- 生成任务配置：`DatasetItem.generate_task_config()` -> `BaseTaskConfig`
  - `BaseTaskConfig = { task, url, user_metadata, eval_config }`
- evaluator：由 `eval_config` 通过 `navi_bench.base.instantiate()` 反射创建
- evaluator 交互模式：
  - `await evaluator.reset()`
  - 每一步 `await evaluator.update(url=..., page=..., ...)`
  - 结束 `await evaluator.compute()` 得到 `FinalResult(score=...)`（以及部分任务的附加字段）

---

## 0.1 运行环境注意：uv 的 cache 目录需要可写

在部分环境里 `$HOME/.cache` 可能被保护为只读，导致 `uv run ...` 报错（Permission denied）。

解决方式是通过环境变量把 uv cache 重定向到 repo 内的可写目录（与
`examples/toolkits/browser_skills_example/run_one_case_end_to_end.sh` 的做法一致）：

```bash
export UV_CACHE_DIR="$PWD/.tmp/uv-cache"
mkdir -p "$UV_CACHE_DIR"
uv run python examples/toolkits/browser_skills_example/run_navi_bench_case.py ...
```

为了避免每次手动设置，本方案新增了一个 wrapper（参考 WebVoyager 的 `run_one_case_end_to_end.sh`）：

- `examples/toolkits/browser_skills_example/run_navi_bench_one.sh`
  - End-to-end：首次跑（空 skills）-> verify -> 抽取 skill -> 二次重跑（带 skills）-> verify + 复用证据
  - 默认使用 `examples/toolkits/browser_skills_example/navi_bench_one.jsonl` 进行单 case 快速迭代
  - 自动设置 `UV_CACHE_DIR="$ROOT_DIR/.tmp/uv-cache"`
  - 默认写入临时目录（`mktemp -d`），避免污染 repo；如需固定路径可用环境变量覆盖 `SKILLS_ROOT/OUT_DIR/TMP_DIR`

---

## 1. 总体设计：把 Navi-Bench Runner 做成 WebVoyager Runner 的“同构替换”

### 1.0 批量跑脚本（对齐 WebVoyager 的 run_google_flights_20.sh）

新增批量脚本：

- `examples/toolkits/browser_skills_example/run_navi_bench_tasks.sh`
  - 默认数据源：`examples/toolkits/browser_skills_example/navi_bench_data.jsonl`
  - 支持 `DOMAIN/START_INDEX/MAX_TASKS/MAX_RETRIES(...)` 等环境变量（风格同 WebVoyager）
  - 内部调用 `run_navi_bench_tasks.py`

### 1.1 新增脚本/组件（建议）

新增一个与 `run_webvoyager_tasks.py` 对齐的 runner：

- `examples/toolkits/browser_skills_example/run_navi_bench_tasks.py`
  - 功能：
    - 从 HF dataset 或本地导出的 Navi-Bench JSONL 加载 tasks
    - 对每个 task：`SkillsAgent.run(...)` 执行
    - verify：调用 Navi-Bench evaluator 给出 `score` 并决定成功/失败
    - 成功：调用 `subtask_extractor.analyze_with_agent(..., auto_save=True)` 抽取 skills
    - 失败：按重试规则 retry，必要时把“失败分析/建议”拼进下一轮 prompt（类似 WebVoyager）
  - 重试规则（按你的要求）：
    - 每 task 最多 5 次（total attempts = 5）
    - 每网站最多 100 次（跨任务累计 attempt cap）

同时建议提供一个单 case 脚本（用于快速迭代）：

- `examples/toolkits/browser_skills_example/run_navi_bench_case.py`
  - 参数：`--task-id navi_bench/<domain>/.../<idx>`，`--split validation`，`--skills-dir` 或 `--skills-root`，`--cdp-port`
  - 输出：打印 session_dir + eval_result 路径

### 1.2 与 WebVoyager 的“同构点”

保持以下行为与 WebVoyager runner 一致：

- 每次 attempt 都写一个独立 session 目录（便于对比与回放）
- attempt 结束前：尽量 capture final evidence（截图/快照）
- attempt 结束时：总是调用 `agent.save_communication_log()` 产出 timeline
- 成功才抽取 skills（避免污染技能库）
- 失败才重试，并把建议注入下一轮 prompt（可选，但建议保留）
- attempt 后关闭浏览器（与现有 runner 行为一致；也降低真实站点状态漂移）

差异点：verify 从 WebJudge 换成 Navi-Bench evaluator（但证据、日志、skill mining 保持一致）。

---

## 2. 关键技术难点：Navi-Bench evaluator 需要 “page.evaluate(JS)” 怎么办？

Navi-Bench 的部分 evaluator（OpenTable/Resy）需要在页面里执行 JS 抽取信息：

- `OpenTableInfoGathering.update(...)` 会 `await page.evaluate(<js_script>)`
- `ResyUrlMatch.update(...)` 既要 URL，也要通过 JS 检测 “no availability” 与抽取 slot

而 Browser Skills 使用的是 `HybridBrowserToolkit`（CDP + 内置 snapshot），不是直接暴露 Playwright `Page`。

### 2.1 目标约束：不把 exec 工具暴露给 agent（只在 runner 内部调用）

为了避免评测动作污染技能库、以及避免 LLM 获得任意 JS 执行能力，本方案明确约束：

- **不把** `browser_console_exec` 加入 `SkillsAgent` 的 enabled tools（`examples/toolkits/browser_skills_example/skill_agent.py` 的 `custom_tools` 保持不变）
- evaluator 所需的 `page.evaluate` 由 **runner 内部** 直接调用底层 `console_exec` 完成

这样做到：

- agent 依旧只会使用“浏览器基础动作工具”，行为可控
- 评测 JS 执行不会进入 action log / timeline（或至少可被过滤）
- 不需要改 ChatAgent 的 FunctionTool schema（避免签名破坏）

### 2.2 PageLike 适配器：用“静默 console_exec”实现 `page.evaluate`

Navi-Bench 的 evaluator（如 `ResyUrlMatch`）只要求一个 `PageLike`：有 `async evaluate(script)` 即可。

实现一个适配器（建议命名 `WsPageAdapter`）：

- `class WsPageAdapter:`
  - `__init__(ws_wrapper)`
  - `async def evaluate(self, script: str) -> Any`
    - 调用 `await ws_wrapper.console_exec_quiet(script)`
    - 解析 TS 返回格式：`"Console execution result: <json>"`
      - strip 前缀
      - `json.loads(<json>)`
    - 容错：解析失败返回 `None`/`[]`，同时把错误写入 `navi_bench_eval_result.json`（避免站点改版导致 runner 直接中断）

#### 新增 quiet API（底层直接调用，避免污染）

当前 `WebSocketBrowserWrapper.console_exec()` 被 `@action_logger` 装饰，会写入 `complete_browser_log.log`，并最终进入 `action_timeline.json`，这会污染 skill mining。

因此建议在 `camel/toolkits/hybrid_browser_toolkit/ws_wrapper.py` 新增一个不记录动作的 API：

- `async def console_exec_quiet(self, code: str) -> Dict[str, Any]:`
  - 直接 `return await self._send_command('console_exec', {'code': code})`
  - 不走 `@action_logger`，因此不会产生 timeline 噪音

同理，如需要获取 URL，也建议提供 `get_tab_info_quiet()`（同样直接 `_send_command('get_tab_info', {})`），供 eval hook 使用，避免额外日志与递归。

---

## 3. 第二个关键难点：evaluator.update 何时调用？（在线 hook vs 事后回放）

Navi-Bench evaluator 的正确用法是“在 agent loop 中持续 update，最后 compute”。

如果只在结束时 update/compute，容易出现：

- agent 访问过正确页面，但结束时离开了；单次 update 看不到（尤其 OpenTable/Resy 的页面态验证）

### 3.1 推荐：在每次浏览器状态改变后自动调用 evaluator.update（在线 hook）

目标：对齐 `navi-bench/demo.py` 的理念（每次导航都 update），但不需要 Playwright event hook。

关键约束：Browser Skills 的 `SkillsAgent.initialize()` 明确避免 wrap browser tools，否则容易破坏 FunctionTool 的严格签名/schema；并且 `ChatAgent` 会在初始化时抓取一份 tools 引用。

因此“runner 侧 monkeypatch toolkit 方法”很容易无效（tools 已经绑定到旧方法），也会带来签名一致性风险。

更稳的实现是：把“每步回调”下沉到 `WebSocketBrowserWrapper.action_logger`（也就是当前 pre_capture/logging 所在的底层），通过 hook callback 在每个动作结束后触发 `evaluator.update`。

#### 方案：action_logger hook callback（推荐落点：ws_wrapper.py）

在 `camel/toolkits/hybrid_browser_toolkit/ws_wrapper.py`：

1) 新增 hook 注册接口（示例）：
   - `def set_action_hook(self, hook: Callable[[ActionHookEvent], Awaitable[None]] | None) -> None`
2) 在 `action_logger` wrapper 内（动作完成后）调用 hook：
   - 只对“可能改变页面状态”的动作触发（visit/click/type/enter/back/forward/switch_tab/scroll/press_key/...）
   - 对 read-only/评测辅助动作跳过（get_tab_info/get_page_snapshot/get_som_screenshot/console_exec/console_view/open_browser/close_browser 等）
3) 递归与噪音控制：
   - 增加一个 ContextVar（例如 `_in_action_hook`）
   - 若 `_in_action_hook` 为 True，则 `action_logger` 直接跳过 hook（防止 hook 内部调用 quiet get_tab_info/console_exec 再次触发 hook）

#### 对 pre_capture 的优化：把“每步 eval/update”并入同一条底层链路

当前 `action_logger` 已经支持 `pre_capture`（pre-step evidence）。本方案不再在 runner/agent 层做“方法 wrapper”，而是把 Navi-Bench 的 `evaluator.update` 也纳入 `action_logger` 的回调链路中：

- 优势：不触碰 FunctionTool/schema，不受工具引用绑定影响（更稳）
- 优势：可以在 wrapper 内复用现有信息，减少重复 I/O：
  - 取 URL 优先从工具输出里的 `tabs` 拿（很多动作返回 tabs）
  - 必要时再走 `get_tab_info_quiet()`（不会写 log）
- 说明：`pre_capture` 仍用于证据抓取（截图/快照），评测 update 用 post-step hook（更符合“动作完成后观察页面状态”）

`ActionHookEvent` 建议包含：

- `action_name`
- `inputs`
- `outputs` / `error`
- `captured_at`
- `current_url`（优先从 outputs.tabs 提取；无 tabs 时调用 `get_tab_info_quiet()`）

#### Runner 侧：NaviBenchEvalHook

runner 在每个 attempt 的生命周期内：

1) `await evaluator.reset()`
2) 从 toolkit 拿到底层 ws_wrapper（建议让 toolkit 提供公开桥接方法；最小实现也可直接调用私有 `_get_ws_wrapper()`）
3) 注册 hook：`ws_wrapper.set_action_hook(eval_hook.on_action)`
4) `eval_hook.on_action(event)` 内：
   - `await evaluator.update(url=event.current_url, page=WsPageAdapter(ws_wrapper))`
   - `WsPageAdapter.evaluate()` 使用 `console_exec_quiet()`，不产生 action log，也不会触发 hook

这样可实现“每步 eval/update”，并且不需要改 SkillsAgent 的工具集合，不会破坏 tool schema，也能覆盖 ActionReplayer 的回放动作。

### 3.2 备选：事后从日志回放（不推荐作为第一版）

理论上也可以：

- 解析 `complete_browser_log.log` 提取所有 URL
- 对 URL-match evaluator 做离线 update

但 OpenTable/Resy 需要当时页面 DOM 状态，离线做不到（除非重放整段浏览器动作并在每步注入 JS），复杂度明显更高。

结论：第一版采用“在线 hook”。

### 3.3 Skill mining 过滤：去掉 console_exec 等评测辅助动作，避免污染

你希望“提取 skill 时过滤掉多余的 exec_console 动作”，建议做两道防线：

1) **源头避免（推荐）**：通过 `console_exec_quiet()` 执行 evaluator JS，默认不会落入 action log，因此不会进入 timeline。
2) **流程过滤（必须加）**：即使未来有人误用 `console_exec`，也能避免污染：
   - 修改 `examples/toolkits/browser_skills_example/analyze_session.py`：
     - 支持 ignore 列表（默认包含 `console_exec`, `console_view`）
     - 可用环境变量覆盖：`SKILL_MINING_IGNORE_ACTIONS=console_exec,console_view`
     - timeline 构造时跳过这些 action
   - 修改 `examples/toolkits/browser_skills_example/subtask_extractor.py`：
     - 在读取 `action_timeline.json` 时再次过滤 ignore 列表（最终进入 `skills_store/**/actions.json` 的动作序列不包含 console 相关动作）

---

## 4. Verify 定义：如何判定 attempt 成功/失败

Navi-Bench evaluator 的 `compute()` 通常返回 `FinalResult(score=...)`：

- Apartments/Resy/GoogleFlights：基本是二值 0/1
- Craigslist：可能是覆盖比例（0~1）
- OpenTable：覆盖比例（0~1）并带 `is_query_covered` 等字段

为了与“成功就抽 skill、失败就重试”的闭环对齐，建议统一成功判定：

- `success := (score >= 1.0 - 1e-9)`（必须满分）

并将 `eval_result` 与更多 debug 信息落盘：

- `<session_dir>/navi_bench_eval_result.json`
  - `task_id`
  - `domain`
  - `website`
  - `attempt`
  - `score`
  - `raw_result`（尽量序列化 pydantic model）
  - `final_url`
  - （可选）对特定 evaluator 提取更强的 debug：
    - `OpenTableInfoGathering`: `is_query_covered`, `n_covered`, `queries`
    - `CraigslistUrlMatch`: `reasoning`
    - `ResyUrlMatch`: 当前实现只在 logger 里打印覆盖原因；建议 runner 在 compute 前后读取对象私有字段（如 `_coverage_reasons`）并 dump

---

## 5. Retry 策略（按要求）

runner 必须维护两类计数器：

1) per-task attempts（每个任务最多 5 次）
2) per-website attempts cap（每个网站累计最多 100 次）

建议接口：

- `--max-attempts-per-task` 固定默认 5
- `--max-attempts-per-website` 固定默认 100

并保持与 WebVoyager runner 类似的 attempt_history 结构，便于后续统计。

### 5.1 失败建议（用于下一次 prompt 注入）

Navi-Bench evaluator 不一定给出可直接用的 suggestions，因此建议实现一个“轻量诊断器”：

- `NaviBenchFailureAdvisor.make_suggestions(task_config, eval_result, evaluator_state, last_snapshot, last_url)`：
  - URL match 任务：把 GT URL/条件（或 normalize 后的目标状态）打印出来，建议 agent “确认筛选条件导致 URL 参数一致”
  - OpenTable/Resy：建议 agent 在结束前回到对应页面并停留；或显式“滚动到可订位的时间段/availability 区域再截图”
  - Google Flights：建议确认是否真的进入 `/flights/search`（Navi-Bench evaluator 只认 search URL）

把 suggestions 拼到下一轮 task 文本末尾（与 WebVoyager 一致）：

```
**IMPORTANT NOTES FROM PREVIOUS ATTEMPT:**
<suggestions>
```

---

## 6. 网站名/域名映射（Skills 目录与 guidelines）

Navi-Bench 的 `domain` 通常是：

- `apartments`
- `craigslist`
- `opentable`
- `resy`
- `google_flights`

而当前 `SkillsAgent` 的 `WEBSITE_GUIDELINES` key 是类似 `"google flights"`、`"wolfram alpha"` 这种空格风格，且不包含 `apartments/craigslist/opentable/resy`。

为避免 `SkillsAgent._get_website_guidelines()` 直接抛错，必须新增/扩展：

- 在 `WEBSITE_GUIDELINES` 增加以下 key（建议全部 lower-case）：
  - `"apartments"` / `"craigslist"` / `"opentable"` / `"resy"` / `"google flights"`（沿用现有）
- 并在 Navi-Bench runner 做映射：
  - `domain == "google_flights"` -> `website="Google Flights"`（传给 SkillsAgent），guideline key 走 `"google flights"`
  - 其它 domain：`website=domain.title()` 或更友好显示，但 guideline key 统一 lower-case

Skills 目录建议按网站分桶（复用现有策略）：

- `<skills_root>/<website_slug>`，其中 website_slug 由 `utils.website_slug()` 生成
  - 例如：`google_flights` -> `google_flights`（或 runner 统一传 `"Google Flights"` 让 slug 变 `google_flights`）

---

## 7. 端到端流程（单 case）——与 WebVoyager 完全同构

以 `task_id = navi_bench/craigslist/.../4` 为例：

1) load task
   - `DatasetItem` from HF split 或本地
   - `task_config = dataset_item.generate_task_config()`
2) build evaluator
   - `evaluator = navi_bench.base.instantiate(task_config.eval_config)`
3) start attempt（最多 5 次）
   - 创建 `SkillsAgent(..., website=..., start_url=task_config.url, enable_skills=True)`
   - `await agent.initialize()`
   - `await evaluator.reset()`
   - 注册 action hook：每次 browser 动作后 `await evaluator.update(url=..., page=WsPageAdapter(ws_wrapper))`
   - `await agent.run(task_config.task)`（task 文本来自 navi-bench，可能包含动态日期渲染后的自然语言）
   - attempt 结束前：
     - `await agent.toolkit.capture_final_evidence()`（best-effort）
     - `eval_result = await evaluator.compute()`（浏览器尚未关闭）
     - `agent.save_communication_log()`（产出 timeline）
     - 写 `navi_bench_eval_result.json`
   - `await agent.toolkit.browser_close()`
4) verify
   - `success := (eval_result.score == 1.0)`
5) success -> extract skills
   - `subtask_extractor.analyze_with_agent(session_dir, skills_dir, auto_save=True)`
6) failure -> retry
   - 生成 suggestions 注入下一轮 prompt
   - 若达到 per-task 或 per-website cap：停止并记录 “skipped”

---

## 8. Batch 流程（可选，但建议一开始就设计好）

建议 `run_navi_bench_tasks.py` 支持：

- `--dataset yutori-ai/navi-bench`
- `--split validation`（或 train/test）
- `--domain craigslist|resy|...`（过滤）
- `--task-id ...`（精确跑单条）
- `--max-tasks N` / `--start K`
- `--skills-root ...` / `--skills-dir ...`（单站时可用 leaf）
- `--run-dir ...`（把每条 task 的 session 都归档到统一目录）
- 固定规则默认值：
  - `max_attempts_per_task=5`
  - `max_attempts_per_website=100`

输出文件建议与 WebVoyager runner 对齐：

- `navi_bench_results.json`（每 task 一条最终结果）
- `navi_bench_run_summary.json`（aggregate + 每站统计 + 复用率）

复用率统计直接复用 `utils.compute_session_summary()` 的 `reuse_ratio_actions/reuse_ratio_calls`。

---

## 9. 风险与缓解

### 9.1 站点改版导致 evaluator JS 失效

- OpenTable/Resy 的 JS 抽取依赖 DOM selector；改版后可能返回空导致误判失败
- 缓解：
  - `WsPageAdapter.evaluate()` 做容错：解析失败返回 `[]`，同时写 debug 到 `navi_bench_eval_result.json`
  - runner 在失败建议里提示“可能站点改版/selector 失效”，并建议人工检查

### 9.2 “最后停留页面”问题

即使在线 hook，最终 compute 可能仍依赖某些最后状态（部分 evaluator）。

- 缓解：
  - 在线 hook：每次动作后都 update，尽量把证据累积在 evaluator 内部
  - runner：compute 前强制再执行一次 `evaluator.update(url=final_url, page=adapter)`（保险）

### 9.3 动态日期导致复现困难

Navi-Bench 任务可能在生成 task_config 时用 `timestamp=None` 取当前时间。

- 缓解（可选增强）：
  - runner 提供 `--fixed-timestamp`，在生成 task_config 前覆盖 dataset item 的 generation config（需要对 config_json 做 patch）
  - 第一版可以先不做，先跑通闭环

---

## 10. 分阶段落地（建议）

Phase 1（最小可用，优先跑通闭环）：

- 新增 `run_navi_bench_case.py` + `run_navi_bench_tasks.py`（同构 WebVoyager）
- 实现 `WsPageAdapter` + `console_exec_quiet()`（evaluator 私下 evaluate，不暴露给 agent）
- 在 `ws_wrapper.action_logger` 增加 action hook callback（在线 update；复用 pre_capture 链路）
- 在 skill mining 增加过滤（`console_exec/console_view` 不进入 timeline/skills）
- verify 规则：`score == 1.0` 才算成功
- 成功后 skill extraction：直接复用 `subtask_extractor.analyze_with_agent`

Phase 2（提升诊断与稳定性）：

- 更丰富的 failure suggestions（按 evaluator 类型输出更可执行的提示）
- `navi_bench_eval_result.json` 加入更多 evaluator 内部 debug（如 Resy 覆盖原因）
- 支持 `--fixed-timestamp` 做可复现评测

Phase 3（联合评测）：

- 在同一 runner 中支持 `webvoyager` 与 `navi-bench` 两种 task source（统一接口）
- 统一输出统计/可视化（复用 `plot_run_results.py`）

---

## 11. 需要你确认的决策点（审批项）

1) 成功判定：是否必须 `score == 1.0`？（建议是；否则技能抽取会把“未完成任务”的轨迹也当成功）
2) verify 只用 Navi-Bench evaluator，还是同时保留 WebJudge 二次验证？
   - 建议：第一版只用 Navi-Bench evaluator（更贴合 benchmark 定义）
3) 是否接受在 `ws_wrapper.py` 增加两个底层 quiet API + hook callback（属于 toolkit 底层改动，但能最大化复用/稳定性）？
   - `console_exec_quiet()` / `get_tab_info_quiet()`
   - `set_action_hook(...)`
4) skills 分桶：按 `domain`（apartments/craigslist/…）还是按显示名（Google Flights）？
   - 建议：以网站显示名为准，但 slug 稳定（`google_flights`）
