import random
import re
from string import punctuation

import gym
import cmudict
import syllables
import sys
import string

from gym.utils import seeding

from llfbench.utils.parser_utils import SimpleGuidanceParser
from llfbench.envs.llf_env import Feedback


class PoemUtil:
    # designed as a Mixin class
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # forwards all unused arguments
        self.cmudict = cmudict.dict()

    def simple_syllable_count(self, word):
        # can also use pip syllables library
        text = word.lower()
        # remove non-alphabets
        text = re.sub('[^a-z]', '', text)

        # count syllables based on phonetics rules
        count = 0
        vowels = 'aeiouy'
        if len(text) == 0:
            return count
        if text[0] in vowels:
            count += 1
        for index in range(1, len(text)):
            if text[index] in vowels and text[index - 1] not in vowels:
                count += 1
        if text.endswith('e'):
            count -= 1
        if text.endswith('le') and text[-3] not in vowels:
            count += 1
        if text.endswith('ed'):
            count -= 1
        if count == 0:
            count += 1
        return count

    def count_syllables(self, line):
        """Use corpora to count syllables in English word or phrase."""
        # prep words for cmudict corpus
        line = line.replace('-', ' ')
        words = line.lower().split()
        num_sylls = 0
        for word in words:
            word = word.strip(punctuation)
            if word.endswith("'s") or word.endswith("’s"):
                word = word[:-2]
            # if word in missing_words:
            #     num_sylls += missing_words[word]
            result = self.cmudict[word]
            # if there is no result, we try to do a simple count
            if len(result) == 0:
                # heuristic based checking
                num_sylls += syllables.estimate(word)  # simple_syllable_count(word)
                continue

            for phonemes in self.cmudict[word][0]:
                for phoneme in phonemes:
                    if phoneme[-1].isdigit():
                        num_sylls += 1
        return num_sylls

    def seed(self, seed):
        pass


class PoemExtractor(object):
    # use LLM to extract the poem
    # just in case more things were written
    def __init__(self, llm, silent=True):
        self.llm = llm
        self.prompt = SimpleGuidanceParser("""
{{#system~}}
You are a helpful assistant.
{{~/system}}

{{#user~}}
Extract only lines of poems in the following message, ignore any part of the message that is not related to the poem.
Only return the poem line by line, including space.

```
{{content}}
```
{{~/user}}

{{#assistant~}}
{{gen 'poem' temperature=0.7}}
{{~/assistant}}
""")

    def __call__(self, content):
        messages = self.prompt(content=content)
        response, info = self.llm.generate(messages)
        return response


class Haiku(PoemUtil, gym.Env):
    def __init__(self, feedback=0, use_extractor=False, seed=None):
        self.assignment = f"Can you write me a haiku? A haiku is a poem that consists of three phrases composed of 17 syllables in a 5, 7, 5 pattern."
        self.form_name = 'Haiku'
        self.use_extractor = use_extractor
        self.extractor = None

        self.feedback = feedback
        self.syllable_req = [5, 7, 5]
        self.syllable_req_str = [str(i) for i in self.syllable_req]
        assert feedback in {0, 0.5, 1}

        self.action_space = gym.spaces.Text(sys.maxsize, charset=string.printable)
        self.observation_space = gym.spaces.Text(sys.maxsize, charset=string.printable)

        self._seed = self.seed(seed)

        self.docstring = self.assignment

        super().__init__()

    def reset(self, **kwargs):
        return self.assignment

    def seed(self, seed=None):
        """Seed the PRNG of this space and possibly the PRNGs of subspaces."""
        self._np_random, seed = seeding.np_random(seed)
        return [seed]

    def initialize_text_extractor(self, poem_extractor: PoemExtractor):
        self.extractor = poem_extractor

    def line_number_incorrect(self, observed_num):
        # The line number is incorrect.
        assert observed_num != len(self.syllable_req)

        improv_direction = "more" if observed_num < len(self.syllable_req) else "less"

        didactic_feedback = Feedback()
        didactic_feedback.r = f"The generated {self.form_name} is incorrect."
        didactic_feedback.fp = f"Write a {self.form_name} that has exactly {len(self.syllable_req)} lines. Write {improv_direction} lines."
        didactic_feedback.fn = f"Do not write a {self.form_name} that has more or less lines than {len(self.syllable_req)}."
        didactic_feedback.hn = f"You wrote {observed_num} lines but the poem needs to be have exactly {len(self.syllable_req)} lines."

        if self.feedback == 0:
            feedback = f"The generated {self.form_name} is incorrect."
        elif self.feedback == 0.5:
            feedback = f"The generated {self.form_name} is incorrect. This is because the {self.form_name} needs to have exactly {len(self.syllable_req)} lines."
        elif self.feedback == 1:
            improv_direction = "more" if observed_num < len(self.syllable_req) else "less"
            feedback = f"The generated {self.form_name} is incorrect. This is because the {self.form_name} needs to have exactly {len(self.syllable_req)} lines. You wrote {observed_num} lines. Write {improv_direction} lines."
        else:
            raise ValueError(f"Invalid feedback level: {self.feedback}")

        return feedback, didactic_feedback

    def line_syllable_check(self, lines):
        success = True
        success_line, total_line = 0, 0
        error_info, success_info = [], []

        for i in range(len(self.syllable_req)):
            # this is to say -- if the generated poem is shorter than required lines
            # we just count the missing line as wrong (for the missing line)
            if i >= len(lines):
                success = False
                total_line += 1
                continue

            line = lines[i]
            count = self.count_syllables(line)
            success *= count == self.syllable_req[i]
            if count != self.syllable_req[i]:
                diff = self.syllable_req[i] - count  # positive: increase syllable; negative: decrease syllable
                error_info.append([i, line, count, diff])
            else:
                success_line += 1
                success_info.append([i, line, count, 0])
            total_line += 1

        return success, success_line / total_line, error_info, success_info

    def produce_line_feedback(self, error_info, success_info):
        # This is called when the line number is correct
        # produce didactic feedback
        didactic_feedback = Feedback()
        if len(error_info) == 0:  # success
            # this is the only place sucess feedback is produced
            didactic_feedback.r = f"The generated {self.form_name} is correct. Congrats! You have successfully produced a poem that matches the assignment description."
            feedback = didactic_feedback.r
            return feedback, didactic_feedback
        else:
            didactic_feedback.r = f"The generated {self.form_name} is incorrect."
            didactic_feedback.hn = f"{self.form_name} needs to have exactly {'-'.join(self.syllable_req_str)} syllables in {len(self.syllable_req)} lines"
            didactic_feedback.hn += ", but lines " if len(error_info) > 1 else ", but line "
            for tup in error_info:
                i, line, count, diff = tup
                # feedback +=  f'The line: "{line}" has {count} syllables. It should only have {self.syllable} syllables' + '\n'
                didactic_feedback.hn += f"{i + 1},"
            didactic_feedback.hn = didactic_feedback.hn[:-1]
            didactic_feedback.hn += " do not." if len(error_info) > 1 else " does not."

            didactic_feedback.hp = "These lines are correct because they have the correct syllables: "
            for tup in success_info:
                i, line, count, diff = tup
                didactic_feedback.hp += f"line {i + 1} has {count} syllables,"
            didactic_feedback.hp = didactic_feedback.hp[:-1]
            didactic_feedback.hp += "."

            didactic_feedback.fp = "Here are some suggestions to fix your error:\n"
            for tup in error_info:
                i, line, count, diff = tup
                improv_direction = "more" if diff > 0 else "less"
                didactic_feedback.fp += f'The line: "{line}" has {count} syllables. It should only have {self.syllable_req[i]} syllables. '
                didactic_feedback.fp += f'You should rewrite the line to have {improv_direction} syllables.' + '\n'

        # now we know there's an error
        if self.feedback == 0:
            # we just say "The generated poem is not correct."
            feedback = f"The generated {self.form_name} is incorrect."
        elif self.feedback == 0.5:
            # we offer an explanation or error message (on exactly which line is at fault)
            # Generated poem is incorrect because <which rule was violated, and where:> poem needs to have exactly 7 syllables in each line, but lines x,y do not.
            feedback = f"The generated {self.form_name} is incorrect.\n"
            feedback += f"This is because {self.form_name} needs to have exactly {'-'.join(self.syllable_req_str)} syllables in {len(self.syllable_req)} lines"
            feedback += ", but lines " if len(error_info) > 1 else ", but line "
            for tup in error_info:
                i, line, count, diff = tup
                feedback += f"{i + 1},"
            feedback = feedback[:-1]
            feedback += " do not." if len(error_info) > 1 else " does not."
        elif self.feedback == 1:
            feedback = f"The generated {self.form_name} is incorrect.\n"
            feedback += "Here are some suggestions to fix your error:\n"
            for tup in error_info:
                i, line, count, diff = tup
                improv_direction = "more" if diff > 0 else "less"
                feedback += f'The line: "{line}" has {count} syllables. It should only have {self.syllable_req[i]} syllables. '
                feedback += f'You should rewrite the line to have {improv_direction} syllables.' + '\n'

        return feedback, didactic_feedback

    def step(self, a):
        """
        LineSyllableConstrainedPoem environment has two latent attributes:
        - Did you have the right number of lines?
        - Did you have the right number of syllables in each line?

        The feedback is structured -- if the line number is wrong, we only provide feedback for the line number.
        (Because it's meaningless to compare syllables)

        If the line number is correct, we provide feedback for the syllables.
        """

        if self.use_extractor:
            if self.extractor is None:
                raise Exception(
                    "Must pass in an extractor through initialize_text_extractor before using the extractor.")
            a = self.extractor(a)

        feedbacks, didactic_feedback = [], Feedback()
        success = True

        lines = []
        for line in a.strip().split('\n'):
            if line == '':
                continue
            lines.append(line)

        if len(lines) != len(self.syllable_req):
            success = False

            feedback, didactic_feedback = self.line_number_incorrect(len(lines))
            feedbacks.append(feedback)
            frac = 0
            # if line numbers are wrong, it's a severe problem, reward we manually set to be 0
        else:
            syllabel_success, frac, error_info, success_info = self.line_syllable_check(lines)
            assert syllabel_success == (len(error_info) == 0)
            success *= syllabel_success

            feedback, didactic_feedback = self.produce_line_feedback(error_info, success_info)
            feedbacks.append(feedback)

        terminal = False  # one step environment

        if type(success) == int:
            success = success == 1

        # observation, reward, terminated, info
        return self.assignment, frac, terminal, {'original_feedback': feedback,
                                                 'feedback': didactic_feedback,
                                                 'success': success}


class Tanka(Haiku):
    def __init__(self, feedback=0, use_extractor=False, seed=None):
        # We can extend this to add "theme" of the poem
        # This increases difficulty a little, but also hard to check if it's thematic or not.
        # feedback=0, use_extractor=False, seed=None
        super().__init__(feedback, use_extractor, seed=seed)
        self.assignment = f"Can you write me a Tanka? A Tanka is a poem that consists of five lines composed of syllables in a 5-7-5-7-7 pattern."
        self.use_extractor = use_extractor
        self.feedback = feedback
        self.syllable_req = [5, 7, 5, 7, 7]
        self.syllable_req_str = [str(i) for i in self.syllable_req]
        self.form_name = 'Tanka'

        self.docstring = self.assignment


class LineSyllableConstrainedPoem(Haiku):
    def __init__(self, syllable_req=[7, 7, 7], feedback=0, use_extractor=False,
                 seed=None):
        # We can extend this to add "theme" of the poem
        # This increases difficulty a little, but also hard to check if it's thematic or not.
        super().__init__(feedback, use_extractor, seed=seed)
        self.syllable_req_str = [str(i) for i in syllable_req]
        self.assignment = f"Can you write me a poem? It should have {len(syllable_req)} lines. The number of syllables for the lines in the poem should follow a {'-'.join(self.syllable_req_str)} pattern."
        self.use_extractor = use_extractor
        self.feedback = feedback
        self.syllable_req = syllable_req
        self.form_name = 'poem'

        self.docstring = self.assignment

        self._seed = self.seed(seed)

    def reset(self, **kwargs):
        if 'seed' in kwargs:
            self._seed = self.seed(kwargs['seed'])

        # create a sampling space
        # Haiku: 3, Tanka: 5, Sonnet: 14, Villanelle: 19, Ballad: 4, Ghazal: 15
        number_of_lines = self._np_random.choice([3, 4, 5, 14, 15, 19])
        # https://www.writing.upenn.edu/~afilreis/88/meter.html
        syllable_sample_space = [5, 7, 8, 9, 10, 17]

        syllable_req = []
        for _ in range(number_of_lines):
            syllable_req.append(self._np_random.choice(syllable_sample_space))

        self.syllable_req_str = [str(i) for i in syllable_req]
        self.syllable_req = syllable_req
        self.assignment = f"Can you write me a poem? It should have {len(syllable_req)} lines. The number of syllables for the lines in the poem should follow a {'-'.join(self.syllable_req_str)} pattern."

        return self.assignment


class SyllableConstrainedPoem(PoemUtil, gym.Env):
    def __init__(self, syllable=7, feedback=0, use_extractor=False, seed=None):

        super().__init__()
        self.assignment = f"Can you produce a short poem where each line has {syllable} syllables?"
        self.syllable = syllable
        self.use_extractor = use_extractor

        self.feedback = feedback
        assert self.feedback in {0, 0.5, 1}

        self.cmudict = cmudict.dict()
        self.extractor = None

        self.action_space = gym.spaces.Text(sys.maxsize, charset=string.printable)
        self.observation_space = gym.spaces.Text(sys.maxsize, charset=string.printable)

        self._seed = self.seed(seed)

        self.docstring = self.assignment

    def reset(self, **kwargs):
        if 'seed' in kwargs:
            self._seed = self.seed(kwargs['seed'])

        # https://www.writing.upenn.edu/~afilreis/88/meter.html
        syllable_sample_space = [5, 7, 8, 9, 10, 17]
        syllable = self._np_random.choice(syllable_sample_space)
        self.syllable = syllable
        self.assignment = f"Can you produce a short poem where each line has {syllable} syllables?"

        return self.assignment

    def seed(self, seed=None):
        """Seed the PRNG of this space and possibly the PRNGs of subspaces."""
        self._np_random, seed = seeding.np_random(seed)
        return [seed]

    def initialize_text_extractor(self, poem_extractor: PoemExtractor):
        self.extractor = poem_extractor

    def get_line_feedback(self, text):
        success = True
        success_line, total_line = 0, 0
        error_info, success_info = [], []
        for i, line in enumerate(text.strip().split('\n')):
            if line == '':
                # this means it's just a segment break
                continue
            count = self.count_syllables(line)
            success *= count == self.syllable
            if count != self.syllable:
                diff = self.syllable - count  # positive: increase syllable; negative: decrease syllable
                error_info.append([i, line, count, diff])
            else:
                success_line += 1
                success_info.append([i, line, count, 0])
            total_line += 1
        return success, success_line / total_line, error_info, success_info

    def step(self, a):
        # observation, reward, terminal, info
        if self.use_extractor:
            if self.extractor is None:
                raise Exception(
                    "Must pass in an extractor through initialize_text_extractor before using the extractor.")
            a = self.extractor(a)
        success, frac, error_info, success_info = self.get_line_feedback(a)

        if success:
            feedback = f"The generated poem is correct. Congrats! You have successfully produced a poem that matches the assignment description."
            didactic_feedback = Feedback(r=feedback)
            return self.assignment, frac, False, {'frac': frac, 'original_feedback': feedback,
                                                  'feedback': didactic_feedback, 'success': True}

        if self.feedback == 0:
            feedback = "The generated poem is incorrect."
        elif self.feedback == 0.5:
            # we offer an explanation or error message (on exactly which line is at fault)
            # Generated poem is incorrect because <which rule was violated, and where> poem needs to have exactly 7 syllables in each line, but lines x,y do not.
            feedback = "The generated poem is incorrect.\n"
            feedback += f"This is because the poem needs to have exactly {self.syllable} syllables in each line"
            feedback += ", but lines " if len(error_info) > 1 else ", but line "
            for tup in error_info:
                i, line, count, diff = tup
                feedback += f"{i + 1},"
            feedback = feedback[:-1]
            feedback += " do not." if len(error_info) > 1 else " does not."
            feedback = "The generated poem is incorrect.\n"
            feedback += "Here are some suggestions to fix your error:\n"
            for tup in error_info:
                i, line, count, diff = tup
                improv_direction = "more" if diff > 0 else "less"
                feedback += f'The line: "{line}" has {count} syllables. It should only have {self.syllable} syllables. '
                feedback += f'You should rewrite the line to have {improv_direction} syllables.' + '\n'
        else:
            raise ValueError(f"Invalid feedback level: {self.feedback}")

        terminal = False  # one step environment

        didactic_feedback = Feedback()
        didactic_feedback.r = "The generated poem is incorrect."

        didactic_feedback.hn = f"The poem needs to have exactly {self.syllable} syllables in all lines"
        didactic_feedback.hn += ", but lines " if len(error_info) > 1 else ", but line "
        for tup in error_info:
            i, line, count, diff = tup
            didactic_feedback.hn += f"{i + 1},"
        didactic_feedback.hn = didactic_feedback.hn[:-1]
        didactic_feedback.hn += " do not." if len(error_info) > 1 else " does not."

        didactic_feedback.hp = "These lines are correct because they have the correct syllables: "
        for tup in success_info:
            i, line, count, diff = tup
            didactic_feedback.hp += f"line {i + 1} has {count} syllables,"
        didactic_feedback.hp = didactic_feedback.hp[:-1]
        didactic_feedback.hp += "."

        didactic_feedback.fp = "Here are some suggestions to fix your error:\n"
        for tup in error_info:
            i, line, count, diff = tup
            improv_direction = "more" if diff > 0 else "less"
            didactic_feedback.fp += f'The line: "{line}" has {count} syllables. It should only have {self.syllable} syllables. '
            didactic_feedback.fp += f'You should rewrite the line to have {improv_direction} syllables.' + '\n'

        out = self.assignment, frac, terminal, {'frac': frac, 'original_feedback': feedback,
                                                "feedback": didactic_feedback, 'success': False}
        return out
