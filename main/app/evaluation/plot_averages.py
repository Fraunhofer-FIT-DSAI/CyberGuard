import matplotlib.pyplot as plt
from tinydb import TinyDB, Query
import os
import numpy as np
from pathlib import Path

models = [
    "llama3.1",
    "gpt-4o-mini-2024-07-18",
    "gpt-4o-2024-08-06",
]

original_colors = {
    "llama3.1": "#0492c2",
    "gpt-4o-mini-2024-07-18": "#3cb043",
    "gpt-4o-2024-08-06": "#d0312d",
}

syntactic_refinement_colors = {
    "llama3.1": "#63c5da",
    "gpt-4o-mini-2024-07-18": "#03c04a",
    "gpt-4o-2024-08-06": "#e3242b",
}

ylabel_to_label = {
    "graph_edit_distance": "Average Normalized Graph Edit Distance",
    "syntactic": "Average Number of Syntactic Errors",
    "metadata": "Average Semantic Accuracy for Metadata",
    "workflow": "Average Semantic Accuracy for Workflow",
    "variables": "Average Semantic Accuracy for Variables",
}

model_to_format = {
    "llama3.1": "o-",
    "gpt-4o-mini-2024-07-18": "^-",
    "gpt-4o-2024-08-06": "s-",
}

all_cases = [
    "baseline",
    "persona",
    "reason",
    "knowledge",
    "one_shot",
    "all_without_one_shot",
    "strongest",
]

case_to_label = {
    "baseline": "Baseline",
    "persona": "Persona",
    "reason": "Reason",
    "knowledge": "Knowledge",
    "one_shot": "One-shot",
    "all_without_one_shot": "All without One-shot",
    "strongest": "All",
}

metrics = [
    "graph_edit_distance",
    "syntactic",
    "time",
    "metadata",
    "workflow",
    "variables",
]


def get_db(model):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, f"../../{model}.json")
    return TinyDB(json_path)


def get_table(model, name):
    database = get_db(model)
    return database.table(name)


def analyze_metric(metric_to_evaluate):
    data = {}
    for model in models:
        table = get_table(model, "results")
        result = table.get(Query().id == "result")
        del result["id"]
        data[model] = result

    plot_data = {}
    for model in models:
        plot_data[model] = [
            (
                data_metric(data[model][case]["original"][metric_to_evaluate]["data"])
                if case in data[model]
                else 0
            )
            for case in all_cases
        ]

    # --- SIZE: 60% height for syntactic & graph_edit_distance; default for others ---
    default_figsize = (10, 8)
    if metric_to_evaluate in ("syntactic", "graph_edit_distance"):
        fig, ax = plt.subplots(figsize=(default_figsize[0], default_figsize[1] * 0.60))
    else:
        fig, ax = plt.subplots(figsize=default_figsize)

    width = 0.25
    x = range(len(all_cases))
    for model in models:
        ax.bar(x, plot_data[model], width, label=model, color=original_colors[model])
        x = [p + width for p in x]

    # --- labels and styling ---
    if metric_to_evaluate in ("metadata", "workflow", "variables"):
        ax.set_ylabel(ylabel_to_label[metric_to_evaluate], fontsize=18)
        ax.tick_params(axis="y", labelsize=18)
        ax.set_xticks([p + width for p in range(len(all_cases))])
        ax.set_xticklabels([case_to_label[case] for case in all_cases],
                           rotation=45, ha="right", fontsize=18)
        # Force y-limit
        ax.set_ylim(0, 0.85)
    else:
        # Default styling for syntactic and graph edit distance
        ax.set_ylabel(ylabel_to_label[metric_to_evaluate], fontsize=12)
        ax.set_xticks([p + width for p in range(len(all_cases))])
        ax.set_xticklabels([case_to_label[case] for case in all_cases],
                           rotation=45, ha="right")

    ax.legend()

    plt.subplots_adjust(hspace=0.5, wspace=0.3)
    plt.tight_layout()
    plt.savefig(output_directory / f"{metric_to_evaluate}.png", dpi=300)
    plt.close(fig)


data_metric = np.mean

BASE_DIR = Path(__file__).resolve().parent
output_directory = BASE_DIR / "figures" / "plot_averages"
output_directory.mkdir(parents=True, exist_ok=True)

metrics = [
    "graph_edit_distance",
    "syntactic",
    "metadata",
    "workflow",
    "variables",
]



for metric in metrics:
    analyze_metric(metric)
