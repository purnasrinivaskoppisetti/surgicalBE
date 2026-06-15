import os
from uuid import uuid4
from fastapi import UploadFile

class LocalStorage:

    @staticmethod
    async def upload_product_image(
        file: UploadFile
    ) -> str:

        upload_dir = "/var/www/surgical/uploads/products"

        os.makedirs(
            upload_dir,
            exist_ok=True
        )

        ext = file.filename.split(".")[-1]

        filename = f"{uuid4()}.{ext}"

        file_path = os.path.join(
            upload_dir,
            filename
        )

        print("=" * 50)
        print("UPLOAD DIR:", upload_dir)
        print("FILE PATH:", file_path)
        print("FILE NAME:", file.filename)

        contents = await file.read()

        print("FILE SIZE:", len(contents))

        with open(
            file_path,
            "wb"
        ) as f:
            f.write(contents)

        print(
            "FILE EXISTS:",
            os.path.exists(file_path)
        )

        print("=" * 50)

        return (
            f"https://api.surgicalworld.org/uploads/products/{filename}"
        )


local_storage = LocalStorage()