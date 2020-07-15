import sys
sys.path.append("..")

import uuid
import bucket
import hashlib

from mock import MagicMock, patch
from collections import UserDict
import pytest

from flask import Flask
app = Flask(__name__)
app.config.update(
    ALLOWED_EXTENSIONS=set(['png']),
    BUCKET_NAME='bucket_name'
)


def test_check_extensions(capsys):
    filename = str(uuid.uuid4()) + '.png'
    extensions = ['png']
    bucket._check_extension(filename, extensions)


def test_check_extensions_throw(capsys):
    filename = str(uuid.uuid4()) + '.gif'
    extensions = ['png']
    with pytest.raises(Exception):
            bucket._check_extension(filename, extensions)
    

def test_check_extensions_throw_noext(capsys):
    filename = str(uuid.uuid4())
    extensions = ['png']
    with pytest.raises(Exception):
            bucket._check_extension(filename, extensions)


@patch('bucket._check_extension')
@patch('bucket._safe_filename')
@patch('bucket.storage')
def test_upload_file(storage_mock, safe_fn_mock, ext_check_mock, capsys):
    with app.app_context():
        client = MagicMock()
        _bucket = MagicMock()
        _blob = MagicMock()
        _bucket.blob.return_value = _blob
        client.bucket.return_value = _bucket
        storage_mock.Client.return_value = client
        
        user_id = str(uuid.uuid4())
        stream = b"image"
        name = str(uuid.uuid4())
        ctype = "png"

        bucket.upload_file(user_id, stream, name, ctype)
        assert client.bucket.called
        assert _bucket.blob.called
        assert _blob.upload_from_string.called
        client.bucket.assert_called_with('bucket_name')
        _bucket.blob.assert_called_with(safe_fn_mock.return_value)
        _blob.upload_from_string.assert_called_with(stream, content_type=ctype)
