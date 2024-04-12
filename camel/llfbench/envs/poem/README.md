# Poem Environment

Each poem environment has an attribute called "assignment" that is the barebone description of what the poem should be.
It usually only contains the name of the poetry form it wants the model to generate.

We introduce two poem environments:
1. `LineSyllableConstrainedPoem` with two specific instantiations: Haiku (5-7-5) and Tanka (5-7-5-7-5), but we can specify any kind of line number + syllable constraints.
2. `SyllableConstrainedPoem`: requires each generated line to have the same number of syllables, but not requirement on number of lines.