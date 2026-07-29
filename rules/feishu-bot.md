# 飞书 bot 后端开发规则

> 本文档由 `claude-code-global` 仓库的 `rules/feishu-bot.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/rules/feishu-bot.md`（CC 端）与 `~/.codex/rules/feishu-bot.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
>
> **触发条件**：Coding Agent 在本轮任务涉及**飞书 bot 后端**——lark-oapi 长连接机器人、事件回调、`im.message.receive` / `card.action.trigger` 等——时，**必须先把本文件读入上下文**，再开始动手。

> **与 `rules/lark.md` 的分工**：那份管**用 lark-cli 创作飞书云文档**（署名约定、docx 实操），本份管**飞书 bot 后端的事件处理**。二者正交，别互相套用。

## 1. 消息幂等去重是必备项，不是优化项

**飞书长连接是 at-least-once 送达**：用 lark-oapi 的 `ws.Client` 收 `im.message.receive` 时，在 ack 超时 / 网络抖动的情况下**飞书会重发同一事件**。实测复现过同一条用户消息间隔约 20 秒被 `_on_message` 处理两次。

代价分两档：

- **只读操作**：多查一次，无害但烦（重复回复很难看）；
- **写操作：是真风险**——重复建用户、重复发确认卡片、重复扣费 / 授权。

**所以任何用 lark-oapi 长连接收消息的机器人都必须做幂等去重**，按事件唯一键（`message_id` / `event_id`）拦掉重复投递。这不是某个项目的业务 bug，是这套送达语义的必然产物。

**去重结构的两条硬要求**：

- **线程安全**：长连接回调可能并发进入，判重 + 记录必须是一个原子动作，不能「先 `in` 再 `add`」中间放手；
- **有界**：必须带 TTL 或 LRU 上限。无界 set 会随运行时长单调增长，最终把常驻进程拖垮——而 bot 恰恰是长期常驻的。

最小骨架：

```python
import threading
from collections import OrderedDict


class SeenEvents:
    """按事件唯一键判重；有界 + 线程安全。"""

    def __init__(self, maxsize: int = 10000) -> None:
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def seen_before(self, key: str) -> bool:
        """首次见到返回 False 并记下；重复投递返回 True。"""
        with self._lock:  # 判重与记录必须原子，否则并发回调会双双判为首次
            if key in self._seen:
                self._seen.move_to_end(key)
                return True
            self._seen[key] = None
            if len(self._seen) > self._maxsize:
                self._seen.popitem(last=False)  # 汰最旧，防无界增长
            return False


_seen = SeenEvents()


def _on_message(event) -> None:
    if _seen.seen_before(event.event.message.message_id):
        return  # 重复投递，直接丢弃
    ...  # 真正的业务处理
```

## 2. 卡片按钮回调需要在开发者后台单独订阅

卡片按钮的回调事件 `card.action.trigger` **需要在飞书开发者后台配置「接收回调」订阅**，否则：**长连接明明连上了、点击卡片却没有任何回调到达。**

这属于**运行前提 / 部署配置**而非代码问题，所以特别值得先查——实测踩过：第一次点卡片毫无反应，代码翻来覆去看不出问题，后台配好订阅后立刻正常。

**排查顺序**：卡片点击无反应时，**先确认后台订阅配了没有**，再去怀疑代码。反过来查会浪费大量时间，因为代码路径看上去完全正确。
