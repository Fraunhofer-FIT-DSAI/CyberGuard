import matplotlib.pyplot as plt
from tinydb import TinyDB, Query
import os
import numpy as np


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
    "llama3.1": "#3944bc",
    "gpt-4o-mini-2024-07-18": "#234f1e",
    "gpt-4o-2024-08-06": "#710c04",
}

model_to_format = {
    "llama3.1": "o",
    "gpt-4o-mini-2024-07-18": "^",
    "gpt-4o-2024-08-06": "s",
}


case_to_label = {
    "baseline": "Baseline",
    "persona": "Persona",
    "reason": "Reason",
    "knowledge": "Knowledge",
    "one_shot": "One-shot",
    "all_without_one_shot": "All without One-shot",
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
        plot_data[model] = {}
        plot_data[model]["original"] = [
            (
                data_metric(data[model][case]["original"][metric_to_evaluate]["data"])
                if case in data[model]
                else 0
            )
            for case in cases
        ]
        plot_data[model]["syntactic_refinement"] = [
            (
                data_metric(
                    data[model][case]["syntactic_refinement"][metric_to_evaluate][
                        "data"
                    ]
                )
                if case in data[model]
                else 0
            )
            for case in cases
        ]

    fig, ax = plt.subplots(figsize=(10, 10))

    x = range(len(cases))
    offset = np.linspace(-0.2, 0.2, len(models))

    for i, model in enumerate(models):
        ax.scatter(
            x + offset[i],
            plot_data[model]["original"],
            label=f"{model} original",
            color=original_colors[model],
            marker=model_to_format[model],
            s=50,
        )
        ax.scatter(
            x + offset[i],
            plot_data[model]["syntactic_refinement"],
            label=f"{model} after syntactic refinement",
            color=syntactic_refinement_colors[model],
            marker=model_to_format[model],
            s=50,
        )

        for j in range(len(cases)):
            ax.plot(
                [x[j] + offset[i], x[j] + offset[i]],
                [
                    plot_data[model]["original"][j],
                    plot_data[model]["syntactic_refinement"][j],
                ],
                color="gray",
                linestyle="--",
                linewidth=0.5,
            )

    ax.set_ylabel(ylabel_to_label[metric_to_evaluate])
    ax.set_xticks(x)
    ax.set_xticklabels([case_to_label[case] for case in cases], rotation=45, ha="right")
    
    if metric_to_evaluate == "syntactic":
        ax.set_ylim(bottom=-0.5)
    elif metric_to_evaluate == "variables":
        ax.set_ylim(bottom=-0.05)
    else:
        ax.set_ylim(bottom=0)
    ax.legend()

    plt.subplots_adjust(hspace=0.5, wspace=0.3)

    plt.tight_layout()

    output_path = os.path.join(
        output_directory, f"syntactic_refinement_{metric_to_evaluate}.png"
    )
    plt.savefig(output_path)
    plt.close(fig)


data_metric = np.mean
output_directory = "./bsc-thesis/figures/evaluation"

for metric in metrics:
    analyze_metric(metric)
