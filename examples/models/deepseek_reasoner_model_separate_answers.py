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

import re

from camel.agents import ChatAgent
from camel.configs import DeepSeekConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

"""
please set the below os environment:
export DEEPSEEK_API_KEY=""
export GET_REASONING_CONTENT="true"
"""

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_REASONER,
    model_config_dict=DeepSeekConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Please explain in detail how the output sequence of transformer becomes longer"""

# Get response information
response = camel_agent.step(user_msg)


def extract_original_response(content):
    # Remove any <think> tags and their content
    return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()


# Extract original response
original_response = extract_original_response(response.msgs[0].content)
print("Original Response:")
print(original_response)

'''
===============================================================================
Original Response:
The output sequence of a transformer model becomes longer through a combination of architectural design and generation strategies. Here's a detailed breakdown:

### 1. **Autoregressive Generation**
   - **Step-by-Step Token Prediction**: In the decoder of a transformer (e.g., GPT or BART), tokens are generated **autoregressively**, meaning each new token depends on previously generated tokens. For example:
     - At step 1: Generate token \( y_1 \) based on the input (encoder states) and a start token.
     - At step 2: Generate \( y_2 \) using \( y_1 \), and so on.
   - This sequential process inherently extends the output sequence length incrementally.

### 2. **Positional Embeddings**
   - **Dynamic Position Encoding**: Transformers use **positional embeddings** to encode the order of tokens. These embeddings are computed for every position up to a maximum length during training. During inference:
     - For the \( t \)-th generated token, positional embeddings for position \( t \) are added, allowing the model to handle sequences longer than those seen during training (if extrapolation is possible).

### 3. **Masked Self-Attention in the Decoder**
   - **Causal Masking**: The decoder uses a **masked self-attention** mechanism to prevent tokens from attending to future positions. This ensures each token \( y_t \) only depends on \( y_1, y_2, ..., y_{t-1} \).
   - As the sequence grows, the mask dynamically adjusts to include new tokens while maintaining causality.

### 4. **Stopping Criteria**
   - **End-of-Sequence (EOS) Token**: The model is trained to generate an EOS token (e.g., `<|endoftext|>` in GPT) to signal completion. Generation stops when this token is predicted.
   - **Maximum Length**: A predefined maximum sequence length acts as a fallback to prevent infinite loops.

### 5. **Handling Variable-Length Outputs**
   - **Training on Variable-Length Data**: During training, the model learns to generate sequences of varying lengths by processing datasets with diverse input-output pairs (e.g., translations with different source/target lengths).
   - **Teacher Forcing**: The decoder is trained using the entire target sequence (shifted right) with masking, teaching it to predict the next token given prior context.

### 6. **Non-Autoregressive Extensions (Optional)**
   - **Parallel Generation**: Some variants (e.g., Non-Autoregressive Transformers) generate all tokens in parallel by predicting output length upfront. However, this often requires auxiliary components (e.g., a length predictor) and trades quality for speed.

### Example Workflow:
1. **Input**: "Translate to French: Hello"
2. **Step 1**: Model generates "Bonjour" (position 1).
3. **Step 2**: Model generates "!" (position 2) based on "Bonjour".
4. **Step 3**: EOS token is generated, stopping the process.  
   Final Output: "Bonjour!" (longer than input "Hello").

### Key Challenges:
- **Positional Embedding Extrapolation**: Handling sequences longer than those seen in training may degrade performance if positional embeddings don’t generalize.
- **Error Propagation**: Autoregressive models can accumulate errors if early tokens are incorrect.

In summary, transformers produce longer sequences via autoregressive decoding, positional embeddings, causal masking, and dynamic stopping—enabling flexible, context-aware generation.
===============================================================================
'''

# Extract reasoning content
reasoning_pattern = r'<think>(.*?)</think>'
reasoning_match = re.search(
    reasoning_pattern, response.msgs[0].content, re.DOTALL
)
reasoning_response = (
    reasoning_match.group(1).strip() if reasoning_match else ""
)

print("\nReasoning Response:")
print(reasoning_response)
# ruff: noqa: E501,RUF001
'''
===============================================================================
Reasoning Response:
Okay, so I need to figure out how the output sequence of a transformer model can become longer. Let me start by recalling what I know about transformers. They're used in tasks like translation, text generation, etc. The standard transformer model, like the ones used in BERT or GPT, processes input sequences and generates output sequences. But usually, in models like GPT, the output is generated one token at a time, right? So the length is either fixed or determined by some stopping condition like an end-of-sentence token.

But the question is about how the output sequence can become longer. Hmm. Maybe in some cases, the model needs to produce a longer sequence than the input. For example, summarization might take a long document and make a shorter summary, but maybe there are tasks where the output is longer. Wait, no, usually summarization is shorter. Maybe something like text generation where you keep generating until a certain condition, but that's more about variable length rather than making it longer than the input.

Wait, the user is asking about the output sequence becoming longer, not just variable. So how does that happen in the architecture of a transformer? Let me think about the decoder part. In the original transformer paper, the decoder generates outputs autoregressively, meaning each token is generated based on the previous ones. So the output length is determined by the number of steps the model takes before emitting an end token. But that's variable, not necessarily longer. So maybe there's a different approach.

Alternatively, maybe in some non-autoregressive models, the transformer can generate all tokens in parallel. But how do they handle sequence length? Wait, non-autoregressive models often fix the output length in advance, which might be determined by another component. For example, in machine translation, if the input is of length N, the output might be set to N or some multiple. But that's a bit forced.

Another thought: maybe the transformer can dynamically adjust the number of processing steps. But I don't recall standard transformers doing that. They usually process all tokens in parallel through the layers. Wait, but during generation, autoregressive models produce one token at a time, so the sequence grows step by step. So each step adds a new token, making the output longer. But how does the model decide when to stop? It uses something like a maximum length or an end token. But the user is asking about the mechanism that allows the output to become longer.

Wait, maybe in some architectures, the transformer can iteratively refine the output, adding more tokens each iteration. For example, in image generation with transformers, you might have patches that are generated in steps. But for text, perhaps using a transformer in a way that allows inserting tokens in the middle of the sequence, thereby increasing its length. But how would that work with the self-attention mechanism?

Alternatively, maybe using a transformer decoder with a mechanism to repeat certain layers or to generate multiple tokens per step. But I'm not sure. Let me think about the positional encodings. If the model is trained to handle variable-length sequences, the positional encodings need to accommodate that. So during training, the model sees sequences of varying lengths, and during inference, it can generate sequences longer than those seen in training as long as the positional encodings can extrapolate. But that's more about handling longer sequences than making the output longer than the input.

Wait, perhaps the user is referring to the fact that during autoregressive generation, the output is built incrementally, so each step appends a new token. But that's standard. The assistant needs to explain in detail the mechanisms that allow the output to extend beyond the input length. So maybe factors like positional embeddings that support variable lengths, the autoregressive process itself, and the use of end tokens or other stopping conditions.

Also, in some models, like Transformer-XL or those with memory, they can handle longer sequences by caching previous states, but that's about processing longer inputs, not outputs.

Another angle: in sequence-to-sequence tasks, the encoder processes the input, and the decoder generates the output. The decoder's attention over the encoder's states allows it to generate output tokens one by one. So each generated token is conditioned on the encoder's input and the previously generated tokens. The length of the output is determined by the decoding process, which can be longer or shorter than the input.

So, putting it all together, the transformer's decoder uses autoregressive generation, where each step produces a new token, thereby extending the output sequence. The model uses positional embeddings to handle the increasing length, and the self-attention in the decoder ensures that each new token is aware of all previous tokens. The process continues until a stopping criterion is met, which could be generating an end-of-sequence token or reaching a maximum length.

Wait, but in the original transformer model, during training, the decoder is fed the entire target sequence shifted right, and uses masking to prevent attending to future tokens. During inference, it generates tokens one by one, so the output sequence grows incrementally. So the key mechanism is autoregressive generation with masked self-attention in the decoder, allowing each step to add a new token based on the previous ones.

So the output sequence becomes longer because each generation step appends a new token, and this is possible due to the autoregressive nature and the positional embeddings that accommodate the growing length. The model is trained to predict the next token given the previous ones, so during inference, it can keep generating until it decides to stop.

Another possibility is using beam search, where multiple hypotheses are extended step by step, but that's more about improving the quality rather than affecting the length.

Additionally, models can be trained with dynamic output lengths, where the length is predicted first, but that's another approach. For example, some models might predict the length of the output before generating it, but that's less common in standard transformers.

So, the main points are:

1. Autoregressive generation: each token is generated based on previous ones, allowing the sequence to grow step by step.
2. Positional embeddings: allow the model to handle the increasing sequence length by providing position information for each new token.
3. Masked self-attention in the decoder: ensures that each step only attends to previous tokens, enabling the generation process.
4. Stopping criteria: determine when to stop adding new tokens, either by an end token or maximum length.

I think that's the core of it. The transformer's architecture, particularly the decoder with its autoregressive and masked attention mechanisms, along with positional encodings, allows the output sequence to be extended incrementally, making it longer until a stopping condition is met.
===============================================================================
'''
