import os
from uuid import uuid4
from fastapi import UploadFile


class LocalStorage:

    @staticmethod
    async def upload_product_image(
        file: UploadFile
    ) -> str:

        upload_dir = "/var/www/surgical/uploads/products"

        os.makedirs(upload_dir, exist_ok=True)

        ext = file.filename.split(".")[-1]
        filename = f"{uuid4()}.{ext}"

        file_path = os.path.join(upload_dir, filename)

        contents = await file.read()

        with open(file_path, "wb") as f:
            f.write(contents)

        return f"https://api.surgicalworld.org/uploads/products/{filename}"


    @staticmethod
    async def upload_banner_image(
        file: UploadFile
    ) -> str:

        upload_dir = "/var/www/surgical/uploads/banners"

        os.makedirs(upload_dir, exist_ok=True)

        ext = file.filename.split(".")[-1]
        filename = f"{uuid4()}.{ext}"

        file_path = os.path.join(upload_dir, filename)

        contents = await file.read()

        with open(file_path, "wb") as f:
            f.write(contents)

        return f"https://api.surgicalworld.org/uploads/banners/{filename}"


local_storage = LocalStorage()