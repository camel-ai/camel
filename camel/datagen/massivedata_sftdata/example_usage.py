# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import csv

from .text_segmentation import TextSegmenter


def segment_file_to_csv(
    input_file_path,
    output_csv_path,
    max_length=1000,
    overlap_length=100,
    min_segment_length=200,
):
    # Create text segmenter instance
    segmenter = TextSegmenter(
        delimiter="\n\n",  # Use paragraph delimiter
        max_length=max_length,  # Maximum length of each segment
        overlap_length=overlap_length,  # Overlap length
        replace_continuous_spaces=True,  # Replace continuous spaces
        remove_urls=False,  # Keep URLs
        min_segment_length=min_segment_length,  # Minimum segment length
    )

    # Read text from file
    try:
        with open(input_file_path, 'r', encoding='utf-8') as file:
            text = file.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return []

    # Segment the text
    segments = segmenter.segment_text(text)

    # Write segments to CSV
    try:
        with open(
            output_csv_path, 'w', encoding='utf-8', newline=''
        ) as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            writer.writerow(
                [
                    'Segment Number',
                    'Text Content',
                    'Character Length',
                    'Contains Overlap',
                ]
            )

            # Write segments
            for i, segment in enumerate(segments, 1):
                has_overlap = i > 1 and len(segments) > 1
                writer.writerow(
                    [i, segment, len(segment), "Yes" if has_overlap else "No"]
                )

        print(f"\nSegmentation results have been saved to: {output_csv_path}")
        print(f"Total segments: {len(segments)}")
        print(
            f"Average segment length: "
            f"{sum(len(s) for s in segments) / len(segments):.2f} characters"
        )

    except Exception as e:
        print(f"Error writing CSV file: {e}")

    return segments


if __name__ == "__main__":
    # Input and output file paths
    input_file = "sample_text.txt"
    output_file = "segmented_text.csv"

    # Perform segmentation and save to CSV
    segments = segment_file_to_csv(
        input_file_path=input_file,
        output_csv_path=output_file,
        max_length=1000,  # Maximum 1000 characters per segment
        overlap_length=100,  # 100 characters overlap
        min_segment_length=200,  # Minimum segment length of 200 characters
    )
