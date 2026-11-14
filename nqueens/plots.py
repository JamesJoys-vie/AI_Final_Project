"""Matplotlib helpers for report figures."""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


def plot_sat(df: pd.DataFrame):
    df = df.sort_values("N")
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    ax[0].plot(df["N"], df["clauses"], "o-", color="tab:blue")
    ax[0].set(xlabel="N", ylabel="# CNF clauses", title="CNF size (Glucose3 encoding)", yscale="log")
    ax[1].plot(df["N"], df["solve_s"], "o-", label="solve only", color="tab:blue")
    ax[1].plot(df["N"], df["total_s"], "s--", label="encode + load + solve", color="tab:orange")
    ax[1].set(xlabel="N", ylabel="seconds", title="Glucose3 running time", yscale="log")
    ax[1].legend()
    for a in ax:
        a.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    return fig


def plot_min_conflicts(summary: pd.DataFrame):
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    for name, grp in summary.groupby("strategy"):
        grp = grp.sort_values("N")  # Đảm bảo đường nối không bị zig-zag
        ax[0].plot(grp["N"], grp["mean_steps"], "o-", label=name)
        ax[1].plot(grp["N"], grp["mean_time_s"], "o-", label=name)
    ax[0].set(xlabel="N", ylabel="mean steps (solved runs)", title="Steps to solution", xscale="log", yscale="log")
    ax[1].set(xlabel="N", ylabel="mean seconds", title="Running time", xscale="log", yscale="log")
    for a in ax:
        a.grid(True, linestyle="--", alpha=0.5)
        a.legend()
    fig.tight_layout()
    return fig


def plot_convergence(histories: dict, n: int):
    fig, ax = plt.subplots(figsize=(6, 3.6))
    for name, h in histories.items():
        ax.plot(h, label=name)
    ax.set(xlabel="step", ylabel="# conflicted queens", title=f"Convergence, N={n}")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    return fig