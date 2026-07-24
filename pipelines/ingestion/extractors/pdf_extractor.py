import pytesseract
import pdfplumber
import pypdfium2 as pdfium

from .base import ExtractedPage


class PDFExtractor:

    async def extract(self, pdf_path: str):

        pages = []

        pdf = pdfium.PdfDocument(pdf_path)

        with pdfplumber.open(pdf_path) as plumber:

            for i in range(len(pdf)):

                page = pdf[i]

                text = page.get_textpage().get_text_range()

                if len(text.strip()) < 50:

                    bitmap = page.render(scale=2).to_pil()

                    text = pytesseract.image_to_string(
                        bitmap,
                        config="--psm 6",
                    )

                pages.append(
                    ExtractedPage(
                        page_number=i + 1,
                        content=text,
                        content_type="text",
                        metadata={
                            "page": i + 1
                        },
                    )
                )

                table_page = plumber.pages[i]

                tables = table_page.extract_tables()

                for table in tables:

                    markdown = "\n".join(
                        [
                            " | ".join(
                                cell if cell else ""
                                for cell in row
                            )
                            for row in table
                        ]
                    )

                    pages.append(
                        ExtractedPage(
                            page_number=i + 1,
                            content=markdown,
                            content_type="table",
                            metadata={
                                "page": i + 1
                            },
                        )
                    )

        return pages