import uuid

from ftplib import FTP

from fastapi import UploadFile

from app.core.config import settings


class BluehostStorage:

    def __init__(self):

        self.host = settings.FTP_HOST
        self.port = settings.FTP_PORT

        self.username = settings.FTP_USERNAME
        self.password = settings.FTP_PASSWORD

        self.root_dir = settings.FTP_ROOT_DIR
        self.upload_dir = settings.FTP_UPLOAD_DIR

    def connect(self):

        ftp = FTP()

        ftp.connect(
            host=self.host,
            port=self.port
        )

        ftp.login(
            self.username,
            self.password
        )

        return ftp

    def ensure_directory(
        self,
        ftp,
        directory
    ):

        parts = directory.split("/")

        for part in parts:

            if not part:
                continue

            try:
                ftp.cwd(part)

            except Exception:

                ftp.mkd(part)
                ftp.cwd(part)

    async def upload_product_image(
        self,
        image: UploadFile
    ):

        extension = image.filename.split(".")[-1]

        filename = (
            f"{uuid.uuid4()}."
            f"{extension}"
        )

        ftp = self.connect()

        try:

            ftp.cwd("/")

            self.ensure_directory(
                ftp,
                f"{self.root_dir}/{self.upload_dir}"
            )

            image.file.seek(0)

            ftp.storbinary(
                f"STOR {filename}",
                image.file
            )

        finally:

            ftp.quit()

        return (
            f"{settings.SITE_URL}/"
            f"{self.upload_dir}/"
            f"{filename}"
        )


bluehost_storage = BluehostStorage()