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
import unittest

from camel.datagen.self_instruct import (
    KeywordFilter,
    LengthFilter,
    NonEnglishFilter,
    PunctuationFilter,
    RougeSimilarityFilter,
)


class TestLengthFilter(unittest.TestCase):
    def test_within_range(self):
        flt = LengthFilter(min_len=2, max_len=5)
        self.assertTrue(flt.apply("This is four words"))

    def test_too_short(self):
        flt = LengthFilter(min_len=2, max_len=5)
        self.assertFalse(flt.apply("Hello"))  # Only 1 word

    def test_too_long(self):
        flt = LengthFilter(min_len=2, max_len=3)
        self.assertFalse(flt.apply("This is more than three words"))


class TestKeywordFilter(unittest.TestCase):
    def test_no_keywords(self):
        flt = KeywordFilter(keywords=["image", "video"])
        self.assertTrue(
            flt.apply("This is a sample instruction without forbidden words")
        )

    def test_contains_keyword(self):
        flt = KeywordFilter(keywords=["image", "video"])
        self.assertFalse(flt.apply("This instruction contains the word image"))

    def test_case_insensitive(self):
        flt = KeywordFilter(keywords=["IMAGE"])
        self.assertFalse(flt.apply("Here is an Image for you"))


class TestPunctuationFilter(unittest.TestCase):
    def test_no_punctuation_start(self):
        flt = PunctuationFilter()
        self.assertTrue(flt.apply("Hello world!"))

    def test_punctuation_start(self):
        flt = PunctuationFilter()
        self.assertFalse(flt.apply("!Invalid start"))

    def test_number_or_letter_start(self):
        flt = PunctuationFilter()
        self.assertTrue(flt.apply("1. Start with a number"))
        self.assertTrue(flt.apply("A start with a letter"))


class TestNonEnglishFilter(unittest.TestCase):
    def test_english_start(self):
        flt = NonEnglishFilter()
        self.assertTrue(flt.apply("Apple pie is delicious"))

    def test_non_english_start(self):
        flt = NonEnglishFilter()
        self.assertFalse(flt.apply("¿Qué hora es?"))
        self.assertFalse(flt.apply("文字が違います"))


class TestRougeSimilarityFilter(unittest.TestCase):
    def setUp(self):
        # Some existing instructions
        self.existing = [
            "Write a summary of this document.",
            "List the steps to bake a cake.",
            "Explain how photosynthesis works.",
        ]
        self.flt = RougeSimilarityFilter(
            existing_instructions=self.existing, threshold=0.7
        )

    def test_unique_instruction(self):
        # A unique instruction that should have low similarity
        self.assertTrue(
            self.flt.apply("Calculate the integral of x^2 from 0 to 10.")
        )

    def test_similar_instruction(self):
        self.assertFalse(self.flt.apply("Write a summary of this paragraph."))

    def test_no_existing_instructions(self):
        flt_empty = RougeSimilarityFilter(
            existing_instructions=[], threshold=0.7
        )
        self.assertTrue(flt_empty.apply("Any instruction would do"))


if __name__ == "__main__":
    unittest.main()
