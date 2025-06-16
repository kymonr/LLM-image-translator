### [中文][zh] | [English][en]


# Large Language Model Image Translator

This project combines Optical Character Recognition (OCR) with translation technology to achieve cross-language text translation within images. The main workflow is as follows:

1. **OCR Processing**: Extract text and its bounding boxes from input images using the EasyOCR library.
2. **Text Translation**: Call the LLM API to translate the extracted text.
3. **Text Replacement**: Overlay the translated text onto the image at the original positions and with the original styles.
4. **Output Result**: Generate and save the final image with translated text to the output folder.

## Environment Setup

#### Installation Steps

1. Clone the repository to your local machine.
2. Run `pip install easyocr PIL` to install the required Python dependencies.

## Usage Instructions

1. Place the images to be translated in the `input` folder.
2. Fill in the OpenAI-compatible API's `api_key` and `api_url` in the line `translator = Translator(source="English", target="Chinese", apikey=yourapi_key, api_base=yourapi_url)` in the `main.py` script.
3. Run the `main.py` script.
4. The translated results will be saved to the `output` folder.

## Notes

- For the list of supported OCR languages, refer to [this link](https://www.jaided.ai/easyocr/).
- You can adjust the text language, recognition threshold, translation service, or image processing parameters in the script.
- To use the large language model for contextual translation, the text may not correspond one-to-one, which could result in compressed text. This issue currently cannot be resolved.

## Acknowledgments

- [EasyOCR](https://github.com/JaidedAI/EasyOCR) - Core OCR processing library.
- [Pillow (PIL Fork)](https://python-pillow.org/) - Image processing tool library.
- [Original repository python-image-translator](https://github.com/boysugi20/python-image-translator) and [Original author boysugi20](https://github.com/boysugi20).

[en]: https://github.com/jedzqer/LLM-image-translator/blob/master/README_en.md "This README is translated by AI"

[zh]: https://github.com/jedzqer/LLM-image-translator/blob/master/README.md
