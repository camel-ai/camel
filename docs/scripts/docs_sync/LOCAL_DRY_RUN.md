# 本地 Dry Run 步骤

这份文档用于本地验证 `docs-incremental-update` 这条链路是否工作正常。

验证思路：

1. 先准备 `changed_python_files.txt`
2. 再用 `doc_code_map.py` 生成 `impacted_docs.txt`
3. 最后把这两个文件一起交给 `auto_sync_docs_with_chatagent.py`

## 前置条件

- 当前仓库根目录下存在可用的 Python 环境
- 已设置 `OPENAI_API_KEY`
- 建议先只跑单个 impacted doc，缩小验证范围

```bash
export OPENAI_API_KEY=你的key
```

## 示例：验证 Terminal Toolkit 相关改动

下面这组命令适用于当前 `terminal_toolkit` 相关 Python 改动。

### 1. 准备 changed Python 文件列表

```bash
printf '%s\n' \
  'camel/toolkits/terminal_toolkit/go_runtime.py' \
  'camel/toolkits/terminal_toolkit/java_runtime.py' \
  'camel/toolkits/terminal_toolkit/runtime_utils.py' \
  'camel/toolkits/terminal_toolkit/terminal_toolkit.py' \
  'camel/toolkits/terminal_toolkit/utils.py' \
  > changed_python_files.txt
```

### 2. 计算 impacted docs

```bash
python docs/scripts/docs_sync/doc_code_map.py impacted \
  --changed-files-file changed_python_files.txt \
  > impacted_docs.txt
```

查看命中的文档：

```bash
cat impacted_docs.txt
```

当前这组示例改动预期会命中：

```text
docs/mintlify/key_modules/terminaltoolkit.mdx
```

如果你只想验证单个文档，可以直接覆盖 `impacted_docs.txt`：

```bash
printf '%s\n' 'docs/mintlify/key_modules/terminaltoolkit.mdx' > impacted_docs.txt
```

### 3. 实际运行 agent

```bash
ALL_PROXY= all_proxy= HTTP_PROXY= http_proxy= HTTPS_PROXY= https_proxy= \
  .venv/bin/python .camel/skills/docs-incremental-update/scripts/auto_sync_docs_with_chatagent.py \
  --docs-file impacted_docs.txt \
  --changed-files-file changed_python_files.txt \
  --model-platform openai \
  --model-type gpt-5.4
```

## 如何判断结果

正常情况下会出现下面三种结果之一：

- `UPDATED: ...`
  说明链路通了，agent 真的更新了文档
- `SKIP (no doc update needed)`
  说明链路通了，但 agent 判断这次不需要改文档
- 长时间无输出
  说明当前 agent 可能卡在模型调用或工具循环里；如果 2 到 3 分钟都没有新输出，直接 `Ctrl+C` 停掉即可

## 建议

- 第一次验证时，优先只跑一个 impacted doc
- 如果你不想污染当前工作区，先在临时 worktree 里执行这些命令
- 跑完后可以用 `git diff -- docs/mintlify/key_modules docs/mintlify/mcp` 查看生成结果
