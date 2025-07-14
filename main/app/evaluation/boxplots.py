import matplotlib.pyplot as plt
from tinydb import Query
from plot_averages import get_table, models
import json
import os

cases = [
    "baseline",
    "persona",
    "reason",
    "knowledge",
    "one_shot",
    "all_without_one_shot",
    "strongest",
]

ylabel_to_label = {
    "graph_edit_distance": "Average Normalized Graph Edit Distance",
    "syntactic": "Average Number of Syntactic Errors",
    "metadata": "Average Semantic Accuracy for Metadata",
    "workflow": "Average Semantic Accuracy for Workflow",
    "variables": "Average Semantic Accuracy for Variables",
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

OUTILER_VALUE = None


def remove_outlier(data):
    if not OUTILER_VALUE:
        return data
    return [value for value in data if value != OUTILER_VALUE]


def analyze_metric(metric_to_evaluate, model):
    table = get_table(model, "results")
    result = table.get(Query().id == "result")
    del result["id"]

    # Prepare the data for plotting
    plot_data = [
        (
            remove_outlier(result[case]["original"][metric_to_evaluate]["data"])
            if case in result
            else []
        )
        for case in cases
    ]

    fig, ax = plt.subplots(figsize=(10, 8))

    meanprops = dict(marker="o", markerfacecolor="red", markersize=8, linestyle="none")
    boxplot_stats = ax.boxplot(
        plot_data, vert=True, patch_artist=True, showmeans=True, meanprops=meanprops
    )

    # Extract medians and means
    medians = [item.get_ydata()[0] for item in boxplot_stats["medians"]]
    means = [item.get_ydata()[0] for item in boxplot_stats["means"]]

    # Extract whiskers
    whiskers = [item.get_ydata() for item in boxplot_stats["whiskers"]]
    min_values = [min(whisker) for whisker in whiskers]
    max_values = [max(whisker) for whisker in whiskers]

    # Extract fliers
    fliers = [
        [int(value) for value in item.get_ydata()] if item.get_ydata().size > 0 else []
        for item in boxplot_stats["fliers"]
    ]
    print("Fliers:", fliers)

    # Group all metrics by case
    stats_by_case = {
        case: {
            "median": medians[i],
            "mean": means[i],
            "min_whisker": min_values[2 * i],
            "max_whisker": max_values[2 * i + 1],
            # "caps": (caps[2*i], caps[2*i+1]),
            "fliers": fliers[i],
        }
        for i, case in enumerate(cases)
    }

    print("Statistics by case:", json.dumps(stats_by_case, indent=2))

    ax.set_title(model)
    ax.set_ylabel(ylabel_to_label[metric_to_evaluate])
    ax.set_xticks([y + 1 for y in range(len(cases))])
    ax.set_xticklabels([case_to_label[case] for case in cases], rotation=45, ha="right")
    plt.subplots_adjust(hspace=0.5, wspace=0.3)

    plt.tight_layout()

    output_path = os.path.join(
        output_directory, f"box_plot_{model}_{metric_to_evaluate}.png"
    )
    plt.savefig(output_path)
    plt.close(fig)


output_directory = "./bsc-thesis/figures/evaluation"


metric = "syntactic"

for model in models:
    analyze_metric(metric, model)

# analyze_metric("graph_edit_distance")
# analyze_metric("syntactic")
# analyze_metric("time")
# analyze_metric("metadata")
# analyze_metric("workflow")
# analyze_metric("variables")

# models = [
#     "llama3.1",
#     "gpt-4o-mini-2024-07-18",
#     "gpt-4o-2024-08-06",
# ]
