"""
============================================================================
  학습 데이터 균등 분배 시각화 (그래프 1)
  - sbert_hybrid_triplet_balanced_dataset.csv의 Intent별 분포를 보여줌
  - 학술 포스터용 고품질 (dpi=300, 큰 폰트)
============================================================================
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── 한글 폰트 + 스타일 ───────────────────────────────────────────────────────
plt.rc("font", family="Malgun Gothic")
plt.rcParams["axes.unicode_minus"] = False

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 색상 팔레트 (블루/네이비 + 오렌지 강조) ──────────────────────────────────
NAVY       = "#1B2A4A"
BLUE       = "#2E6EB5"
LIGHT_BLUE = "#6BAED6"
ORANGE     = "#E8712B"
GOLD       = "#F5A623"
GRAY       = "#9E9E9E"
BG         = "#FAFBFD"

# ── 폰트 크기 (포스터용 - 멀리서도 보이게) ───────────────────────────────────
T_TITLE = 22
T_LABEL = 16
T_TICK  = 13
T_ANNOT = 13
DPI     = 300


def fig_balanced_distribution():
    # ── 데이터 로드 ──────────────────────────────────────────────────────────
    csv_path = os.path.join(
        os.path.dirname(OUT_DIR),
        "ragTest", "data", "processed",
        "sbert_hybrid_triplet_balanced_dataset.csv"
    )
    df = pd.read_csv(csv_path)
    vc = df["Intent"].value_counts().sort_values(ascending=True)

    intents = vc.index.tolist()
    counts  = vc.values
    mean_val = counts.mean()
    std_val  = counts.std()
    n_total  = counts.sum()

    # ── Intent 라벨 정리 (snake_case → 읽기 좋게) ────────────────────────────
    def format_label(s):
        return s.replace("_", " ").title()

    labels = [format_label(i) for i in intents]

    # ── 그래프 생성 ──────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(11, 7.5))
    fig.patch.set_facecolor("white")

    y_pos = np.arange(len(labels))

    # 막대 색상: 평균 이상 → BLUE, 평균 미만 → LIGHT_BLUE
    bar_colors = [BLUE if c >= mean_val else LIGHT_BLUE for c in counts]

    bars = ax.barh(
        y_pos, counts, height=0.68,
        color=bar_colors, edgecolor=NAVY, linewidth=0.6, zorder=3
    )

    # ── 각 막대에 샘플 수 표시 ───────────────────────────────────────────────
    for bar, c in zip(bars, counts):
        ax.text(
            c + 1.5, bar.get_y() + bar.get_height() / 2,
            f"{c}", ha="left", va="center",
            fontsize=T_ANNOT, fontweight="bold", color=NAVY
        )

    # ── 평균선 (오렌지 점선) ─────────────────────────────────────────────────
    ax.axvline(
        x=mean_val, color=ORANGE, linestyle="--", linewidth=2.5, zorder=4
    )
    ax.text(
        mean_val + 1.5, len(labels) - 0.3,
        f"Mean = {mean_val:.1f}",
        fontsize=T_ANNOT + 2, fontweight="bold", color=ORANGE,
        bbox=dict(
            boxstyle="round,pad=0.35", fc="white", ec=ORANGE, alpha=0.9
        )
    )

    # ── ±1σ 범위 음영 (균등함 강조) ──────────────────────────────────────────
    ax.axvspan(
        mean_val - std_val, mean_val + std_val,
        color=GOLD, alpha=0.12, zorder=1,
        label=f"Mean ± 1σ ({mean_val - std_val:.0f}–{mean_val + std_val:.0f})"
    )

    # ── 통계 요약 박스 (우측 하단) ────────────────────────────────────────────
    stats_text = (
        f"Total Samples: {n_total:,}\n"
        f"Categories: {len(intents)}\n"
        f"Mean: {mean_val:.1f}  |  Std: {std_val:.1f}\n"
        f"Range: {counts.min()} – {counts.max()}"
    )
    ax.text(
        0.97, 0.05, stats_text,
        transform=ax.transAxes, ha="right", va="bottom",
        fontsize=T_ANNOT, color=NAVY,
        bbox=dict(
            boxstyle="round,pad=0.5", fc=BG, ec=GRAY, alpha=0.95
        )
    )

    # ── 축 & 스타일 ─────────────────────────────────────────────────────────
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=T_TICK, color=NAVY)
    ax.set_xlim(0, max(counts) + 18)
    ax.set_xlabel("Number of Triplet Samples", fontsize=T_LABEL, color=NAVY)
    ax.set_title(
        "Balanced Training Data Distribution by Intent",
        fontsize=T_TITLE, fontweight="bold", color=NAVY, pad=18
    )
    ax.tick_params(axis="x", labelsize=T_TICK, colors=NAVY)
    ax.grid(axis="x", alpha=0.3, linestyle="--", zorder=0)
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_color(GRAY)
        sp.set_linewidth(0.8)

    # ── 범례 ─────────────────────────────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(color=BLUE, label=f"≥ Mean ({mean_val:.0f})"),
        mpatches.Patch(color=LIGHT_BLUE, label=f"< Mean ({mean_val:.0f})"),
        plt.Line2D([0], [0], color=ORANGE, ls="--", lw=2.5, label="Mean"),
        mpatches.Patch(color=GOLD, alpha=0.3, label="Mean ± 1σ"),
    ]
    ax.legend(
        handles=legend_handles, loc="lower right",
        fontsize=T_TICK, framealpha=0.9,
        bbox_to_anchor=(0.99, 0.22)
    )

    # ── 저장 ─────────────────────────────────────────────────────────────────
    path = os.path.join(OUT_DIR, "fig_balanced_distribution.png")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Poster Figure - Balanced Distribution")
    print("=" * 60)
    fig_balanced_distribution()
    print("=" * 60 + "\n")
