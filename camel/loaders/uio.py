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
from typing import List
from camel.loaders import UnstructuredIO

from concurrent.futures import ThreadPoolExecutor

class MultiSourceParser:
    def __init__(self):
        self.uio = UnstructuredIO()
        self.clean_options = [
            ('replace_unicode_quotes', {}),
            ('clean_dashes', {}),
            ('clean_non_ascii_chars', {}),
            ('clean_extra_whitespace', {}),
        ]

    def parse_multiple_sources(self, sources: List[str], chunk_size: int = 6000, overlap: int = 1) -> List[str]:
        r"""Parse multiple files or URLs and return chunked, cleaned text.
        
        Args:
            sources: List of file paths or URLs to parse
            chunk_size: Maximum characters per chunk
            chunk_overlap: Number of overlapping chunks
            
        Returns:
            List of cleaned text chunks
        """
        all_elements = []
        
        # Parse all sources in parallel
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.uio.parse_file_or_url, source): source for source in sources}
            for future in futures:
                try:
                    elements = future.result()
                    if elements is not None:  # Only extend if elements were successfully parsed
                        all_elements.extend(elements)
                    else:
                        source = futures[future]
                        print(f"Warning: No elements extracted from {source}")
                except Exception as e:
                    source = futures[future]
                    print(f"Error processing {source}: {str(e)}")
        
        if not all_elements:
            print("No elements were successfully parsed from any sources")
            return []
            
        # Combine all elements
        combined_text = "\n\n".join([str(el) for el in all_elements])
        
        # Chunk the combined text
        chunks = self.uio.chunk_elements(
            elements=all_elements,
            chunk_type="chunk_by_title",
            max_characters=chunk_size,
            overlap=overlap
        )
        
        # Clean each chunk in parallel
        cleaned_chunks = []
        with ThreadPoolExecutor() as executor:
            cleaned_chunks = list(executor.map(
                lambda chunk: self.uio.clean_text_data(text=str(chunk), clean_options=self.clean_options),
                chunks
            ))
            
        return cleaned_chunks

def parse_sources(sources: List[str], chunk_size: int = 6000, overlap: int = 1) -> List[str]:
    r"""Convenience function to parse multiple sources.
    
    Args:
        sources: List of file paths or URLs to parse
        chunk_size: Maximum characters per chunk
        overlap: if or not overlap
        
    Returns:
        List of cleaned text chunks
    """
    parser = MultiSourceParser()
    return parser.parse_multiple_sources(sources, chunk_size=chunk_size, overlap=overlap)
# Example usage with line profiling
if __name__ == "__main__":
    sources = [
        "https://docs.camel-ai.org/cookbooks/data_generation/sft_data_generation_and_unsloth_finetuning_Qwen2_5_7B.html",
        "https://docs.camel-ai.org/cookbooks/data_generation/self_instruct_data_generation.html",
        "https://docs.camel-ai.org/cookbooks/data_generation/cot_data_gen_sft_qwen_unsolth_upload_huggingface.html",
        "https://docs.camel-ai.org/cookbooks/data_generation/synthetic_dataevaluation%26filter_with_reward_model.html",
        "https://docs.camel-ai.org/cookbooks/data_generation/data_model_generation_and_structured_output_with_qwen.html#",
      
    ]
    
    chunks=parse_sources(sources)
    # Print chunks (optional)
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}:")
        print(chunk)
        print("\n" + "-" * 80)