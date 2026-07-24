import pandas as pd

from .base import ExtractedPage


class CSVExtractor:

    async def extract(self, csv_path: str):

        df = pd.read_csv(csv_path)

        pages = []

        if len(df) < 1000:

            # Small CSV → Markdown table
            for start in range(0, len(df), 100):

                block = df.iloc[start:start + 100]

                markdown = block.to_markdown(index=False)

                pages.append(
                    ExtractedPage(
                        page_number=(start // 100) + 1,
                        content=markdown,
                        content_type="table",
                        metadata={
                            "rows": len(block)
                        },
                    )
                )

        else:

            # Large CSV → Summary
            summary = []

            summary.append(f"Rows: {len(df)}")
            summary.append(f"Columns: {len(df.columns)}")

            for column in df.columns:

                if pd.api.types.is_numeric_dtype(df[column]):

                    summary.append(
                        f"{column}: "
                        f"min={df[column].min()}, "
                        f"max={df[column].max()}, "
                        f"mean={df[column].mean()}"
                    )

                else:

                    summary.append(
                        f"{column}: "
                        f"{df[column].value_counts().head(5).to_dict()}"
                    )

            pages.append(
                ExtractedPage(
                    page_number=1,
                    content="\n".join(summary),
                    content_type="text",
                    metadata={
                        "summary": True
                    },
                )
            )

            # Sample rows in 100-row blocks
            for start in range(0, len(df), 100):

                block = df.iloc[start:start + 100]

                pages.append(
                    ExtractedPage(
                        page_number=(start // 100) + 2,
                        content=block.to_markdown(index=False),
                        content_type="table",
                        metadata={
                            "rows": len(block)
                        },
                    )
                )

        return pages