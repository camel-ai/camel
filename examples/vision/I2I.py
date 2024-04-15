from image_understanding import understanding_image
from image_craft import craft_image
def main():
    image_paths = ['test_0.jpg', 'test_1.jpg']
    captions = understanding_image(image_paths)

    for caption in captions:
        craft_image(caption)


main()
