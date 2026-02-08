"""Sample analysis script for data-analyzer skill."""


def analyze(data):
    """Analyze data and return statistics."""
    if not data:
        return {"error": "No data provided"}
    return {
        "count": len(data),
        "sum": sum(data),
        "mean": sum(data) / len(data),
        "min": min(data),
        "max": max(data),
    }


if __name__ == "__main__":
    # Example usage
    sample_data = [10, 20, 30, 40, 50]
    result = analyze(sample_data)
    print(f"Analysis result: {result}")
