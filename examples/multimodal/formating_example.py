from typing import List

from camel.prompts import MultiModalPrompt, TextPrompt

if __name__=="__main__":
    # example prompt for simple one image vqa, using default model input format
    vqa_prompt = MultiModalPrompt(text_prompt=TextPrompt("Please anwser the following question about the given image:\nQuestion: {Question}"), modalities=["CAMEL_IMAGE"])

    print("Example prompt for simple one image vqa, using default model input format:")

    question1 = "What animal is in the picture?"
    question2 = "What is the color of the animal?"

    image1_path = "examples/multimodal/camel.jpg"
    image2_path = "examples/multimodal/llama.jpg"

    vqa_prompt1 = vqa_prompt.format(Question=question1, CAMEL_IMAGE=image1_path)
    vqa_prompt2 = vqa_prompt.format(Question=question2, CAMEL_IMAGE=image2_path)
    
    print("vqa_prompt1:")
    print(vqa_prompt1.to_model_format())

    print("vqa_prompt2:")
    print(vqa_prompt2.to_model_format())


    print("-"*100)

    # example prompt for multiple image question, with custom model input format
    def multi_image_input_format(text_prompt,modalities_dict):
        r"""
        Label the image in the front of text prompt with numbers. 
        The multi image indexing format is taken from MMICL: Empowering Vision-language Model with Multi-Modal In-Context Learning
        [Image{i}] in the prompt would be replaced by the visual prompts for the i-th image.
 
        Returns:
            dict: The input format that the multimodal model can understand.
        """

        if not isinstance(modalities_dict["CAMEL_IMAGE"], List):
            modalities_dict["CAMEL_IMAGE"] = [modalities_dict["CAMEL_IMAGE"]]


        for i, image in enumerate(modalities_dict["CAMEL_IMAGE"]):
            text_prompt = f"Image {i} is <Image{i}> [Image{i}]\n" + text_prompt

        return {"prompt": text_prompt, "image": modalities_dict["CAMEL_IMAGE"]}



    question3 = "Are the animals from the two images the same?"
    multi_image_prompt = vqa_prompt.format(Question=question3, CAMEL_IMAGE=[image1_path, image2_path]) # easily apply custom input format for different VLM agents

    print(r"Example prompt for multiple image question, with custom model input format(<Image{i}> is the special token, [Image{i}] is the image visual prompt]):")
    print("multi_image_prompt: \n")
    
    model_input = multi_image_prompt.to_model_format(multi_image_input_format)
    
    prompt = model_input["prompt"]
    print(prompt)

    images = model_input["image"]
    print("images:")
    print(images)