from datasets import load_dataset

# Load dataset
ds = load_dataset("HuggingFaceH4/MATH-500")
print(ds)

# Export the dataset to a JSON file
ds["test"].to_json("./downloadeddata_files/HuggingFaceH4_MATH-500.json")

print("Dataset has been saved as a JSON file: ./downloadeddata_files/HuggingFaceH4_MATH-500.json")