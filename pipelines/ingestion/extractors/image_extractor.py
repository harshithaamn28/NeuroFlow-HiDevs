from PIL import Image
import pytesseract

from .base import ExtractedPage


class ImageExtractor:

    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def extract(self, image_path: str):

        image = Image.open(image_path)

        image.thumbnail((1024, 1024))

        ocr_text = pytesseract.image_to_string(image)

        description = await self.llm_client.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image in detail."
                        },
                        {
                            "type": "image",
                            "image": image_path
                        }
                    ]
                }
            ],
            routing_criteria={
                "require_vision": True
            }
        )

        content = (
            description.content
            + "\n\nText found in image:\n"
            + ocr_text
        )

        return [
            ExtractedPage(
                page_number=1,
                content=content,
                content_type="image_description",
                metadata={}
            )
        ]