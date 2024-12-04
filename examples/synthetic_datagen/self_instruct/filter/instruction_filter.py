from camel.synthetic_datagen.self_instruct.filter import *

instruction_filter = InstructionFilter()
instruction_filter.add_filter(LengthFilter(min_len=5, max_len=200))
instruction_filter.add_filter(
    KeywordFilter(keywords=["forbidden", "avoid"]))
instruction_filter.add_filter(PunctuationFilter())
instruction_filter.add_filter(NonEnglishFilter())
existing_instructions = ["This is an example instruction."]
instruction_filter.add_filter(
    RougeSimilarityFilter(existing_instructions=existing_instructions,
                          threshold=0.7))
instructions = [
    "Describe the effects of pollution.",
    "forbidden keyword should be avoided.",
    "!Invalid starting punctuation.",
    "这是一个非英文开头的指令。",
    "This is an example instruction."
]

filtered_instructions = instruction_filter.filter(instructions)

print(filtered_instructions)