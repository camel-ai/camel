#!/usr/bin/env python3

from pathlib import Path

import graphviz


def convert_dot_to_pdf(dot_file: Path):
    """Convert a DOT file to PDF using graphviz."""
    try:
        # Read the DOT file
        with open(dot_file, "r") as f:
            dot_content = f.read()

        # Create a graph from the DOT content
        graph = graphviz.Source(dot_content)

        # Generate PDF
        graph.render(dot_file.stem, format="pdf", cleanup=True)
        print(f"Successfully converted {dot_file} to {dot_file.stem}.pdf")
    except Exception as e:
        print(f"Error converting {dot_file}: {str(e)}")


def main():
    # Get the directory of this script
    current_dir = Path(__file__).parent

    # Find all DOT files in the current directory
    dot_files = list(current_dir.glob("*.dot"))

    if not dot_files:
        print("No DOT files found in the current directory.")
        return

    print(f"Found {len(dot_files)} DOT files to convert.")

    # Convert each DOT file to PDF
    for dot_file in dot_files:
        convert_dot_to_pdf(dot_file)


if __name__ == "__main__":
    main()
