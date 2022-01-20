import cgi
import mimetypes
import os
import pathlib
import re
from html import unescape
from typing import Optional, Tuple
from uuid import uuid4
from urllib.parse import unquote

from furl import furl
from scrapy.http import Response


class FileSaver:
    folder_size: int
    folder_number: int
    select_folder: str

    def __init__(self, base_folder: str, bucket_prefix: str, max_bucket_size: int):
        self.base_folder: str = os.path.abspath(base_folder)
        self.bucket_prefix: str = bucket_prefix
        self.max_bucket_size: int = max_bucket_size  # maximum number of files

        if not os.path.exists(self.base_folder):
            os.mkdir(self.base_folder)

        sequence = [
            (folder.name, int(folder.name.replace(self.bucket_prefix, '')))
            for folder in os.scandir(self.base_folder)
            if folder.is_dir() and self.bucket_prefix in folder.name
        ]

        if sequence:
            folder_name, max_folder_number = max(sequence, key=lambda result: result[1])
        else:
            max_folder_number = 1
            folder_name = ''.join([self.bucket_prefix, str(max_folder_number)])

        self.folder_number: int = max_folder_number
        self.select_folder = os.path.join(self.base_folder, folder_name)

        if os.path.exists(self.select_folder):
            self.folder_size = len(next(os.walk(self.select_folder))[2])
        else:
            os.mkdir(self.select_folder)
            self.folder_size = 0

        if self._is_folder_full():
            self._change_folder()

    def _increment_folder_size(self) -> None:
        self.folder_size += 1

    def _change_folder(self) -> None:
        self.folder_number += 1
        self.select_folder = os.path.join(
            self.base_folder,
            ''.join([self.bucket_prefix, str(self.folder_number)])
        )

        self.folder_size = 0

        if not os.path.exists(self.select_folder):
            os.mkdir(self.select_folder)

    def _is_folder_full(self) -> bool:
        return self.folder_size >= self.max_bucket_size

    def save_file(
        self,
        response: Response,
        filename_prefix: str = '',
        filename: Optional[str] = None
    ) -> Tuple[str, str]:
        if 'Content-Type' in response.headers:
            content_type: str = response.headers['Content-Type'].decode()
            if content_type.startswith('image/') or \
               content_type.startswith('audio/') or \
               content_type.startswith('application/pdf'):
                raw_filename: str = furl(response.url).path.segments[-1]
                raw_filename = re.search('^[^?;#.]*', raw_filename).group() + mimetypes.guess_extension(content_type)
            else:
                raise Exception('Unsupported content type')
        elif 'Content-Disposition' in response.headers:
            _, params = cgi.parse_header(response.headers['Content-Disposition'].decode())
            if 'filename*' in params:
                raw_filename: str = unquote(unescape(params['filename*'])).lstrip("utf-8''")
            else:
                raw_filename: str = unescape(params['filename'])
        else:
            raise Exception('Unsupported file type')

        original_filename = re.sub('[~/]', '_', raw_filename)
        file_type = pathlib.Path(original_filename).suffix

        if not filename:
            filename: str = str(uuid4().hex)
        filename = filename_prefix + filename

        path_to_file: str = os.path.join(self.select_folder, f'{filename}{file_type}')

        with open(path_to_file, 'wb') as writer:
            writer.write(response.body)

        self._increment_folder_size()
        if self._is_folder_full():
            self._change_folder()

        return path_to_file, original_filename
