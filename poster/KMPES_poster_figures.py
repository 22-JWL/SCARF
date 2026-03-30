"""
============================================================================
  KMPES 포스터 논문용 시각화 (4개 그래프)
  SCARF: 반도체 후공정 장비 자연어 제어를 위한 다단계 모호성 탐지 프레임워크

  출력 파일 (poaster/ 폴더):
    fig1_accuracy.png   - 정확도 비교
    fig2_latency.png    - 소요 시간 비교
    fig3_multiturn.png  - ProCoT 다중 턴 분포
    fig4_pipeline.png   - SCARF 파이프라인 지연 시간

  실행:
    cd poaster
    python KMPES_poster_figures.py
============================================================================
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ══════════════════════════════════════════════════════════════════════════════
#  한글 폰트 + 스타일
# ══════════════════════════════════════════════════════════════════════════════
plt.rc("font", family="Malgun Gothic")
plt.rcParams["axes.unicode_minus"] = False

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# 색상 팔레트
NAVY       = "#1B2A4A"
BLUE       = "#2E6EB5"
LIGHT_BLUE = "#6BAED6"
ORANGE     = "#E8712B"
GOLD       = "#F5A623"
GRAY       = "#9E9E9E"
BG         = "#FAFBFD"

# 폰트 크기
T_TITLE = 20
T_LABEL = 16
T_TICK  = 14
T_ANNOT = 15
DPI     = 300


def _style(ax, title="", xlabel="", ylabel=""):
    ax.set_title(title, fontsize=T_TITLE, fontweight="bold", color=NAVY, pad=16)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=T_LABEL, color=NAVY)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=T_LABEL, color=NAVY)
    ax.tick_params(labelsize=T_TICK, colors=NAVY)
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_color(GRAY)
        sp.set_linewidth(0.8)


# ══════════════════════════════════════════════════════════════════════════════
#  그래프 1 - 정확도 비교
# ══════════════════════════════════════════════════════════════════════════════
def fig1_accuracy():
    fig, ax = plt.subplots(figsize=(7, 5.5))
    fig.patch.set_facecolor("white")

    names = ["ProCoT\n(GPT)", "SCARF\n(Ours)"]
    vals  = [85.71, 90.37]
    cols  = [GRAY, BLUE]

    bars = ax.bar(names, vals, width=0.48, color=cols,
                  edgecolor=NAVY, linewidth=1.2, zorder=3)

    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.35,
                f"{v:.2f}%", ha="center", va="bottom",
                fontsize=T_ANNOT + 2, fontweight="bold", color=NAVY)

    # 차이 화살표
    ax.annotate("", xy=(1, vals[1]), xytext=(0, vals[0]),
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=2.5,
                                connectionstyle="arc3,rad=0.15"))
    mid_y = (vals[0] + vals[1]) / 2 + 0.6
    ax.text(0.5, mid_y, f"+{vals[1]-vals[0]:.2f}%p",
            ha="center", fontsize=T_ANNOT + 1, fontweight="bold", color=ORANGE)

    ax.set_ylim(80, 95)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="y", alpha=0.3, linestyle="--", zorder=0)
    _style(ax, "API URL Accuracy", ylabel="Accuracy (%)")

    path = os.path.join(OUT_DIR, "fig1_accuracy.png")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


# ══════════════════════════════════════════════════════════════════════════════
#  그래프 2 - 소요 시간 비교
# ══════════════════════════════════════════════════════════════════════════════
def fig2_latency():
    fig, ax = plt.subplots(figsize=(7, 5.5))
    fig.patch.set_facecolor("white")

    names = ["ProCoT\n(GPT)", "SCARF\n(Ours)"]
    vals  = [5.904, 0.214]
    cols  = [GRAY, BLUE]

    bars = ax.bar(names, vals, width=0.48, color=cols,
                  edgecolor=NAVY, linewidth=1.2, zorder=3)

    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15,
                f"{v:.3f}s", ha="center", va="bottom",
                fontsize=T_ANNOT + 2, fontweight="bold", color=NAVY)

    ratio = vals[0] / vals[1]
    ax.annotate(f"x{ratio:.1f} faster",
                xy=(1, vals[1] + 0.05), xytext=(0.7, 3.8),
                fontsize=T_ANNOT + 3, fontweight="bold", color=ORANGE,
                arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=2.5),
                bbox=dict(boxstyle="round,pad=0.35", fc=GOLD, ec=ORANGE, alpha=0.25))

    ax.set_ylim(0, 7.5)
    ax.grid(axis="y", alpha=0.3, linestyle="--", zorder=0)
    _style(ax, "Avg. Inference Latency", ylabel="Time (sec)")

    path = os.path.join(OUT_DIR, "fig2_latency.png")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


# ══════════════════════════════════════════════════════════════════════════════
#  그래프 3 - ProCoT 다중 턴 분포
# ══════════════════════════════════════════════════════════════════════════════
def fig3_multiturn():
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.patch.set_facecolor("white")

    turns  = [1, 2, 3, 4, 5, 6, 7, 9]
    counts = [65, 38, 42, 27, 34, 1, 9, 2]
    x = np.arange(len(turns))

    bars = ax.bar(x, counts, width=0.62, color=LIGHT_BLUE,
                  edgecolor=NAVY, linewidth=1.0, zorder=3)

    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, c + 1.2,
                str(c), ha="center", va="bottom",
                fontsize=T_ANNOT, fontweight="bold", color=NAVY)

    # 평균 2.90턴 세로 점선 (턴1=idx0, 턴2=idx1 → 2.90 = idx 1.90)
    avg_x = 1.0 + 0.90
    ax.axvline(x=avg_x, color=ORANGE, ls="--", lw=2.5, zorder=4)
    ax.text(avg_x + 0.18, max(counts) * 0.90,
            "Avg. 2.90 turns", fontsize=T_ANNOT + 1, fontweight="bold",
            color=ORANGE,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=ORANGE, alpha=0.9))

    ax.set_xticks(x)
    ax.set_xticklabels([str(t) for t in turns])
    ax.set_ylim(0, max(counts) + 12)
    ax.grid(axis="y", alpha=0.3, linestyle="--", zorder=0)
    _style(ax, "ProCoT Multi-turn Distribution",
           xlabel="Turn Count", ylabel="Queries")

    path = os.path.join(OUT_DIR, "fig3_multiturn.png")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


# ══════════════════════════════════════════════════════════════════════════════
#  그래프 4 - SCARF 파이프라인 구간별 지연 시간 (가로 누적 막대)
# ══════════════════════════════════════════════════════════════════════════════
def fig4_pipeline():
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white")

    labels = ["Stage 1\nRetriever", "Stage 2\nClassifier", "Stage 3\nInference"]
    times  = [0.025, 0.021, 0.214]
    colors = [LIGHT_BLUE, BLUE, NAVY]
    total  = sum(times)

    left = 0.0
    h = 0.50
    for i, (lab, t, c) in enumerate(zip(labels, times, colors)):
        ax.barh(0, t, left=left, height=h, color=c,
                edgecolor="white", linewidth=2, zorder=3)
        left += t

    # Stage 1·2 는 좁으므로 위쪽에 annotation
    ax.annotate(f"Stage 1\n0.025s  (9.6%)",
                xy=(times[0] / 2, h / 2), xytext=(times[0] / 2, 0.65),
                ha="center", va="bottom",
                fontsize=T_TICK, fontweight="bold", color=LIGHT_BLUE,
                arrowprops=dict(arrowstyle="-|>", color=LIGHT_BLUE, lw=1.5))

    ax.annotate(f"Stage 2\n0.021s  (8.1%)",
                xy=(times[0] + times[1] / 2, h / 2),
                xytext=(times[0] + times[1] / 2 + 0.04, 0.65),
                ha="center", va="bottom",
                fontsize=T_TICK, fontweight="bold", color=BLUE,
                arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.5))

    # Stage 3 - 넓으므로 바 안에 표시
    s3_cx = times[0] + times[1] + times[2] / 2
    ax.text(s3_cx, 0, f"Stage 3\n0.214s  (82.3%)",
            ha="center", va="center",
            fontsize=T_ANNOT, fontweight="bold", color="white", zorder=5)

    # 합계
    ax.text(total + 0.012, 0,
            f"Total\n{total:.3f}s", ha="left", va="center",
            fontsize=T_ANNOT + 1, fontweight="bold", color=ORANGE)

    # Stage 3 세부 주석
    ax.text(total / 2, -0.58,
            "Stage 3 detail  -  Clear (LLM): 0.392s   |   Ambiguous (Slot Filling): 0.100s",
            ha="center", va="top", fontsize=T_TICK, color=NAVY, style="italic")

    ax.set_xlim(0, total + 0.14)
    ax.set_ylim(-0.80, 1.05)
    ax.set_yticks([])
    ax.grid(axis="x", alpha=0.3, linestyle="--", zorder=0)
    _style(ax, "SCARF Pipeline Latency Breakdown", xlabel="Time (sec)")

    path = os.path.join(OUT_DIR, "fig4_pipeline.png")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  KMPES Poster - Figure Generation")
    print("=" * 60)

    fig1_accuracy()
    fig2_latency()
    fig3_multiturn()
    fig4_pipeline()

    print("\n  All 4 figures saved to:", OUT_DIR)
    print("=" * 60 + "\n")
