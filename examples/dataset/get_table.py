import json
from pathlib import Path

evol_results = json.load(open(Path("generated_data_evolved.json"), "r", encoding="utf-8"))  

# Analyze and display scores in markdown table format
print("\nAnalyzing evolution scores:")

# Initialize table data
table_data = []

# Process each generation
for gen_num, generation in enumerate(evol_results):
    gen_data = []
    # Process each iteration in the generation
    for iter_key in sorted(generation.keys(), key=int):
        iter_data = []
        instructions = generation[iter_key]
        if isinstance(instructions, list):
            for instruction in instructions:
                if "scores" in instruction and instruction["scores"]:
                    scores = instruction["scores"]
                    score_values = [
                        scores.get("diversity", 0),
                        scores.get("difficulty", 0),
                        scores.get("validity", 0),
                        scores.get("solvability", 0)
                    ]
                    avg_score = sum(score_values) / len(score_values)
                    content = f"{score_values[0]},{score_values[1]},{score_values[2]},{score_values[3]}:{avg_score:.2f}"
                    iter_data.append(content)
        gen_data.append(iter_data)
    table_data.append(gen_data)

if table_data:
    # Find maximum number of samples across all generations and iterations
    max_samples = max(max(len(iter_data) for iter_data in gen_data) for gen_data in table_data)
    max_iters = max(len(gen_data) for gen_data in table_data)
    
    # Calculate maximum content length for each column
    col_widths = {
        "gen": len("Generation"),
        "iter": len("Iteration"),
        "samples": [0] * max_samples,
        "avg": len("Average")
    }
    
    # Update column widths based on actual content
    for gen_data in table_data:
        for iter_data in gen_data:
            for i, score in enumerate(iter_data):
                if i < max_samples:
                    col_widths["samples"][i] = max(col_widths["samples"][i], len(score))
    
    # Create format strings for each column
    gen_format = f"| {{:<{col_widths['gen']}}} "
    iter_format = f"| {{:<{col_widths['iter']}}} "
    sample_formats = [f"| {{:<{width}}} " for width in col_widths["samples"]]
    avg_format = f"| {{:<{col_widths['avg']}}} |"
    
    # Print markdown table header
    headers = gen_format.format("Generation") + iter_format.format("Iteration")
    for i in range(max_samples):
        headers += sample_formats[i].format(f"Sample {i}")
    headers += avg_format.format("Average")
    
    # Create separator line
    inter = "|" + "-" * (col_widths["gen"] + 2) + "|" + "-" * (col_widths["iter"] + 2)
    for width in col_widths["samples"]:
        inter += "|" + "-" * (width + 2)
    inter += "|" + "-" * (col_widths["avg"] + 2) + "|"

    print(headers)
    print(inter)
    
    # Print data rows
    for gen_num, gen_data in enumerate(table_data):
        for iter_num, iter_data in enumerate(gen_data):
            row = gen_format.format(f"Gen {gen_num}") + iter_format.format(f"Iter {iter_num}")
            all_sample_scores = []
            
            # Add each sample's scores to the row
            for i, score in enumerate(iter_data):
                row += sample_formats[i].format(score)
                score_value = float(score.split(":")[1])
                all_sample_scores.append(score_value)
            
            # Pad with empty cells if needed
            for i in range(len(iter_data), max_samples):
                row += sample_formats[i].format("-")
            
            # Calculate and add the average
            if all_sample_scores:
                avg_score = sum(all_sample_scores) / len(all_sample_scores)
                row += avg_format.format(f"{avg_score:.2f}")
            else:
                row += avg_format.format("-")
            
            print(row)
        
        # Add a separator line between generations
        if gen_num < len(table_data) - 1:
            print(inter)

    # Print summary
    print("\nSummary:")
    print(f"Total generations: {len(table_data)}")
    print(f"Maximum iterations per generation: {max_iters}")
    print(f"Maximum samples per iteration: {max_samples}")
    total_samples = sum(sum(len(iter_data) for iter_data in gen_data) for gen_data in table_data)
    print(f"Total scored samples: {total_samples}")
    
    # Calculate averages
    if total_samples > 0:
        avg_samples_per_iter = total_samples / sum(len(gen_data) for gen_data in table_data)
        print(f"Average samples per iteration: {avg_samples_per_iter:.1f}")