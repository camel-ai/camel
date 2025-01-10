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
class TextSegmenter:
    def __init__(
        self,
        delimiter="\n\n",
        max_length=5000,
        overlap_length=50,
        replace_continuous_spaces=True,
        remove_urls=False,
        min_segment_length=100,
    ):
        """
        Initialize the text segmenter with given parameters.

        Args:
            delimiter (str): The delimiter to split text into segments
            max_length (int): Maximum length of each segment in tokens
            overlap_length (int): Number of tokens to overlap between segments
            replace_continuous_spaces (bool): Whether to replace continuous
                spaces/tabs
            remove_urls (bool): Whether to remove URLs from text
            min_segment_length (int): Minimum length for a segment before
                merging
        """
        if not isinstance(max_length, int) or max_length <= 0:
            raise ValueError("max_length must be a positive integer")
        if not isinstance(overlap_length, int) or overlap_length < 0:
            raise ValueError("overlap_length must be a non-negative integer")
        if overlap_length >= max_length:
            raise ValueError("overlap_length must be less than max_length")

        self.delimiter = delimiter
        self.max_length = max_length
        self.overlap_length = overlap_length
        self.replace_continuous_spaces = replace_continuous_spaces
        self.remove_urls = remove_urls
        self.min_segment_length = min_segment_length

        # 预编译正则表达式
        import re

        self.space_pattern = re.compile(r'[ \t]+')
        self.newline_pattern = re.compile(r'\n+')
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        self.email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
        self.chinese_pattern = re.compile(r'[.!?;]')

    def preprocess_text(self, text):
        """
        Preprocess text according to the rules.

        Args:
            text (str): Input text to preprocess

        Returns:
            str: Preprocessed text
        """
        if not isinstance(text, str):
            raise ValueError("Input text must be a string")

        if self.replace_continuous_spaces:
            # Replace continuous spaces and tabs with single space
            text = self.space_pattern.sub(' ', text)
            # Replace continuous newlines with single newline
            text = self.newline_pattern.sub('\n', text)

        if self.remove_urls:
            # Remove URLs
            text = self.url_pattern.sub('', text)
            # Remove email addresses
            text = self.email_pattern.sub('', text)

        return text.strip()

    def merge_short_segments(self, segments):
        """
        Merge segments that are too short.

        Args:
            segments (list): List of text segments

        Returns:
            list: List of merged text segments
        """
        if not segments:
            return segments

        merged = []
        current = segments[0]

        for i in range(1, len(segments)):
            if len(current) < self.min_segment_length and i < len(segments):
                current += self.delimiter + segments[i]
            else:
                merged.append(current)
                current = segments[i]

        if current:
            merged.append(current)

        return merged

    def segment_text(self, text):
        """
        Segment the input text according to the configured parameters.

        Args:
            text (str): Input text to segment

        Returns:
            list: List of text segments
        """
        # Preprocess text
        text = self.preprocess_text(text)

        # Split text by delimiter and Chinese sentence endings
        segments = []
        initial_segments = text.split(self.delimiter)

        for segment in initial_segments:
            # Further split by Chinese sentence endings if needed
            chinese_sentences = self.chinese_pattern.split(segment)
            segments.extend(s.strip() for s in chinese_sentences if s.strip())

        # Process segments
        result_segments = []
        current_segment = ""

        for segment in segments:
            # If adding this segment would exceed max_length
            if (
                len(current_segment + self.delimiter + segment)
                > self.max_length
            ):
                if current_segment:
                    result_segments.append(current_segment)

                # If single segment is longer than max_length, split it
                if len(segment) > self.max_length:
                    words = segment.split()
                    current_segment = ""
                    for word in words:
                        if len(current_segment + " " + word) > self.max_length:
                            result_segments.append(current_segment)
                            current_segment = word
                        else:
                            current_segment += (
                                " " + word if current_segment else word
                            )
                else:
                    current_segment = segment
            else:
                current_segment += (
                    self.delimiter + segment if current_segment else segment
                )

        # Add the last segment if it exists
        if current_segment:
            result_segments.append(current_segment)

        # Merge short segments
        result_segments = self.merge_short_segments(result_segments)

        # Handle overlap
        if self.overlap_length > 0 and len(result_segments) > 1:
            overlapped_segments = []
            for i in range(len(result_segments)):
                if i == 0:
                    overlapped_segments.append(result_segments[i])
                else:
                    # Add overlap from previous segment
                    prev_segment = result_segments[i - 1]
                    overlap = (
                        prev_segment[-self.overlap_length :]
                        if len(prev_segment) > self.overlap_length
                        else prev_segment
                    )
                    overlapped_segments.append(
                        overlap + self.delimiter + result_segments[i]
                    )

            return overlapped_segments

        return result_segments


# Example usage
if __name__ == "__main__":
    # Example text
    example_text = """This is a sample text.
    It contains multiple paragraphs and some     extra spaces.
    
    This is another paragraph with a URL: https://example.com
    And an email: example@email.com
    
    Let's see how it gets segmented."""

    # Create segmenter with default settings
    segmenter = TextSegmenter()

    # Segment the text
    segments = segmenter.segment_text(example_text)

    # Print results
    print("Segmented text:")
    for i, segment in enumerate(segments, 1):
        print(f"\nSegment {i}:")
        print(segment)
