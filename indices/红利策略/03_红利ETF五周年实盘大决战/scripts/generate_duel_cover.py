#!/usr/bin/env python3
"""生成《第2战 嘉实300红利低波 vs 华泰红利低波》商业特稿宽屏封面。

设计规范：
- 宽屏比例 2.18:1 (1200 x 550, 导出高清 3000 x 1375)
- 深邃买方金融科技深蓝背景 (#0A0F1D)
- 只体现核心观点与核心数据反差，杜绝多余小字与视觉杂质
- 现代克制、字体重心居中对齐、左右留白严格对称
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as patches

# 路径
OUTPUT_DIR = Path("indices/红利策略/03_红利ETF五周年实盘大决战/charts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "02_嘉实300红利低波ETF_特稿宽屏封面.png"

# 字体配置
candidates = ["PingFang SC", "Hiragino Sans GB", "Heiti SC", "Arial Unicode MS", "Noto Sans CJK SC", "SimHei"]
available = {font.name for font in fm.fontManager.ttflist}
family = next((name for name in candidates if name in available), "sans-serif")
print(f"Using font family: {family}")

# 画布设置: 12 x 5.5 英寸 (宽屏 ~2.18:1)
fig = plt.figure(figsize=(12, 5.5), dpi=250, facecolor="#0B1120")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_facecolor("#0B1120")
ax.axis("off")

# 1. 顶部微光装饰线与小徽标
# 顶部 3px 渐变质感顶边
ax.plot([0.05, 0.95], [0.965, 0.965], color="#3B82F6", alpha=0.4, linewidth=1.2)
ax.plot([0.35, 0.65], [0.965, 0.965], color="#60A5FA", alpha=0.9, linewidth=2.0)

# 顶部系列胶囊标签 (Centered)
tag_box = patches.FancyBboxPatch(
    (0.33, 0.88), 0.34, 0.058,
    boxstyle="round,pad=0.008,rounding_size=0.025",
    facecolor="#1E293B", edgecolor="#334155", linewidth=1.0, alpha=0.9
)
ax.add_patch(tag_box)
ax.text(
    0.50, 0.909,
    "红利 ETF 5周年实盘大决战 · 第 2 战",
    color="#93C5FD", fontsize=11, weight="semibold", fontfamily=family,
    ha="center", va="center"
)

# 2. 核心命题主标题 (两只对垒与核心叩问)
ax.text(
    0.50, 0.775,
    "选股池限死在沪深 300，到底是稳妥还是作茧自缚？",
    color="#F8FAFC", fontsize=22, weight="heavy", fontfamily=family,
    ha="center", va="center"
)

# 3. 核心观点金句副标题 (反差算账)
ax.text(
    0.50, 0.675,
    "实盘 7 年终局账单：为少挨 1.96% 的回撤，每年少赚 3.58% 的复利！",
    color="#F59E0B", fontsize=13.5, weight="bold", fontfamily=family,
    ha="center", va="center"
)

# 4. 核心数据对比三联卡片 (左右对称排布: 0.08, 0.38, 0.68 各宽 0.24)
card_w = 0.26
card_h = 0.28
card_y = 0.31

cards_data = [
    {
        "x": 0.08,
        "title": "7年累计总回报",
        "bench_val": "+125.8%",
        "duel_val": "+78.4%",
        "diff_text": "少赚 -47.4 pp",
        "diff_sub": "终点财富落后 26.6%",
        "tag_color": "#EF4444",
        "bg_color": "#131D31",
        "border_color": "#1E2E4A"
    },
    {
        "x": 0.37,
        "title": "年化复合回报 (CAGR)",
        "bench_val": "11.88%",
        "duel_val": "8.30%",
        "diff_text": "每年少赚 -3.58 pp",
        "diff_sub": "复利出现断层滑落",
        "tag_color": "#EF4444",
        "bg_color": "#131D31",
        "border_color": "#1E2E4A"
    },
    {
        "x": 0.66,
        "title": "全周期最大回撤",
        "bench_val": "-16.52%",
        "duel_val": "-14.56%",
        "diff_text": "仅浅 +1.96 pp",
        "diff_sub": "防守安慰剂代价昂贵",
        "tag_color": "#10B981",
        "bg_color": "#131D31",
        "border_color": "#1E2E4A"
    }
]

for c in cards_data:
    # 卡片外框
    box = patches.FancyBboxPatch(
        (c["x"], card_y), card_w, card_h,
        boxstyle="round,pad=0.012,rounding_size=0.03",
        facecolor=c["bg_color"], edgecolor=c["border_color"], linewidth=1.2
    )
    ax.add_patch(box)
    
    cx = c["x"] + card_w / 2.0
    
    # 卡片指标名称
    ax.text(cx, card_y + card_h - 0.045, c["title"], color="#94A3B8", fontsize=10.5, weight="medium", fontfamily=family, ha="center", va="center")
    
    # 双方数值对比 (华泰 50 vs 嘉实 300)
    ax.text(cx - 0.065, card_y + card_h - 0.11, "华泰 50", color="#64748B", fontsize=8.5, fontfamily=family, ha="center", va="center")
    ax.text(cx - 0.065, card_y + card_h - 0.155, c["bench_val"], color="#E2E8F0", fontsize=12, weight="bold", fontfamily=family, ha="center", va="center")
    
    ax.text(cx, card_y + card_h - 0.135, "vs", color="#475569", fontsize=9.5, fontfamily=family, ha="center", va="center")
    
    ax.text(cx + 0.065, card_y + card_h - 0.11, "嘉实 300", color="#64748B", fontsize=8.5, fontfamily=family, ha="center", va="center")
    ax.text(cx + 0.065, card_y + card_h - 0.155, c["duel_val"], color="#38BDF8", fontsize=12, weight="bold", fontfamily=family, ha="center", va="center")
    
    # 底部核心差异胶囊标签
    pill_w = card_w - 0.035
    pill_h = 0.068
    pill_x = c["x"] + 0.0175
    pill_y = card_y + 0.025
    pill = patches.FancyBboxPatch(
        (pill_x, pill_y), pill_w, pill_h,
        boxstyle="round,pad=0.005,rounding_size=0.02",
        facecolor="#1E293B", edgecolor=c["tag_color"], linewidth=1.0, alpha=0.95
    )
    ax.add_patch(pill)
    ax.text(cx, pill_y + pill_h * 0.62, c["diff_text"], color=c["tag_color"], fontsize=10.5, weight="heavy", fontfamily=family, ha="center", va="center")
    ax.text(cx, pill_y + pill_h * 0.24, c["diff_sub"], color="#94A3B8", fontsize=7.5, fontfamily=family, ha="center", va="center")

# 5. 底部一锤定音总结条 (平实简洁大白话结论)
summary_box = patches.FancyBboxPatch(
    (0.08, 0.11), 0.84, 0.11,
    boxstyle="round,pad=0.01,rounding_size=0.025",
    facecolor="#0F172A", edgecolor="#334155", linewidth=1.1
)
ax.add_patch(summary_box)

ax.text(
    0.50, 0.185,
    "【终局结论】 嘉实 300红利低波 ETF 定分 79.5 分（落后基准 5.5 分）",
    color="#E2E8F0", fontsize=11, weight="bold", fontfamily=family,
    ha="center", va="center"
)

ax.text(
    0.50, 0.138,
    "两头不靠：防守深度不及景顺 100（回撤 -13.9%），长跑复利望不到华泰 50（落后 47%）",
    color="#94A3B8", fontsize=9.5, fontfamily=family,
    ha="center", va="center"
)

# 保存
plt.savefig(OUTPUT_PATH, dpi=250, bbox_inches="tight", pad_inches=0.02)
plt.close(fig)
print(f"特稿宽屏封面生成成功: {OUTPUT_PATH}")
