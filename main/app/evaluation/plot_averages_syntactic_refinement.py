# plot_averages_syntactic_refinement.py
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from tinydb import TinyDB, Query
import os
import numpy as np
from pathlib import Path

# ----------------------- data/config -----------------------
models = [
    "llama3.1",
    "gpt-4o-mini-2024-07-18",
    "gpt-4o-2024-08-06",
]

# marker per model (to match the attached plot)
model_to_marker = {
    "llama3.1": "s",          # square
    "gpt-4o-mini-2024-07-18": "o",  # circle
    "gpt-4o-2024-08-06": "^",       # triangle
}

# line style per model (for the vertical connectors)
model_to_linestyle = {
    "llama3.1": "-",                 # solid
    "gpt-4o-mini-2024-07-18": "--",  # dashed
    "gpt-4o-2024-08-06": ":",        # dotted
}

case_to_label = {
    "baseline": "Baseline",
    "persona": "Persona",
    "reason": "Reason",
    "knowledge": "Knowledge",
    "one_shot": "One-shot",
    "all_without_one_shot": "All w/o One-shot",
    "strongest": "All",
}

ylabel_to_label = {
    "graph_edit_distance": "Average Normalized Graph Edit Distance",
    "syntactic": "Average Number of Syntactic Errors",
    "metadata": "Average Semantic Accuracy for Metadata",
    "workflow": "Average Semantic Accuracy for Workflow",
    "variables": "Average Semantic Accuracy for Variables",
}

cases = [
    "baseline",
    "persona",
    "reason",
    "knowledge",
    "one_shot",
    "all_without_one_shot",
    "strongest",
]

metrics = [
    "graph_edit_distance",
    "syntactic",
    "metadata",
    "workflow",
    "variables",
]

# ----------------------- IO helpers -----------------------
def get_db(model):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, f"../../{model}.json")
    return TinyDB(json_path)

def get_table(model, name):
    database = get_db(model)
    return database.table(name)

# ----------------------- plotting -------------------------
def analyze_metric(metric_to_evaluate):
    # collect data (means) from JSONs
    data = {}
    for model in models:
        table = get_table(model, "results")
        result = table.get(Query().id == "result")
        if result and "id" in result:
            del result["id"]
        data[model] = result or {}

    plot_data = {}
    for model in models:
        plot_data[model] = {
            "original": [
                (data_metric(data[model][c]["original"][metric_to_evaluate]["data"])
                 if c in data[model] else 0)
                for c in cases
            ],
            "syntactic_refinement": [
                (data_metric(data[model][c]["syntactic_refinement"][metric_to_evaluate]["data"])
                 if c in data[model] else 0)
                for c in cases
            ],
        }

    if metric_to_evaluate == "syntactic":
        fig, ax = plt.subplots(figsize=(14, 8 * 0.65))  # reduced height
    else:
        fig, ax = plt.subplots(figsize=(14, 8))

    x = np.arange(len(cases))
    offset = np.linspace(-0.25, 0.25, len(models))

    legend_elems = []
    for i, model in enumerate(models):
        mkr = model_to_marker[model]
        ls = model_to_linestyle[model]

        # scatter points
        ax.scatter(x + offset[i], plot_data[model]["original"],
                   s=90, marker=mkr, facecolors="black", edgecolors="black", linewidths=1)
        ax.scatter(x + offset[i], plot_data[model]["syntactic_refinement"],
                   s=90, marker=mkr, facecolors="white", edgecolors="black", linewidths=1.5)

        # connectors
        for j in range(len(cases)):
            ax.plot([x[j] + offset[i], x[j] + offset[i]],
                    [plot_data[model]["original"][j], plot_data[model]["syntactic_refinement"][j]],
                    color="black", linestyle=ls, linewidth=1.5, alpha=0.9)

        # legend entries
        legend_elems.append(Line2D([], [], marker=mkr, linestyle=ls, color="black",
                                   markerfacecolor="black", markeredgecolor="black", markersize=8,
                                   label=f"{pretty_model(model)} Original"))
        legend_elems.append(Line2D([], [], marker=mkr, linestyle=ls, color="black",
                                   markerfacecolor="white", markeredgecolor="black", markersize=8,
                                   label=f"{pretty_model(model)} Refined"))

    # --- axis labels and legends ---
    if metric_to_evaluate == "syntactic":
        ax.set_ylabel(ylabel_to_label[metric_to_evaluate], fontsize=13)
        ax.set_xticks(x)
        ax.set_xticklabels([case_to_label[c] for c in cases], rotation=35, ha="right", fontsize=11)

        ax.legend(handles=legend_elems, title="Model & Version",
                  frameon=True, fontsize=10, title_fontsize=11,
                  loc="upper right")   # inside
    else:
        ax.set_ylabel(ylabel_to_label[metric_to_evaluate], fontsize=20)  
        ax.tick_params(axis="y", labelsize=18)  
        ax.set_xticks(x)
        ax.set_xticklabels([case_to_label[c] for c in cases],
                           rotation=35, ha="right", fontsize=22)
        # force y-axis range
        if metric_to_evaluate == "graph_edit_distance":
            ax.set_ylim(0, 0.6)
        else:
            ax.set_ylim(0, 0.85)
        # legend outside, 3 columns, smaller font
        ax.legend(handles=legend_elems, title="Model & Version",
                  frameon=True, fontsize=14, title_fontsize=16,
                  ncol=3, loc="upper center",
                  bbox_to_anchor=(0.5, 1.25))  # push outside

    plt.tight_layout()
    plt.savefig(output_directory / f"syntactic_refinement_{metric_to_evaluate}.png", dpi=300)
    plt.close(fig)

def pretty_model(m):
    # shorter names for legend to match the example’s feel
    if m == "llama3.1":
        return "Llama 3.1"
    if m.startswith("gpt-4o-mini"):
        return "GPT-4o-mini"
    if m.startswith("gpt-4o-"):
        return "GPT-4o"
    return m

# aggregation function
data_metric = np.mean

# output dir
BASE_DIR = Path(__file__).resolve().parent
output_directory = BASE_DIR / "figures" / "syntactic_refinement"
output_directory.mkdir(parents=True, exist_ok=True)

# generate all metrics (the attached plot is for "syntactic")
for metric in metrics:
    analyze_metric(metric)
