import sys
sys.path.append("..")

import uuid
import main
import hashlib

from mock import MagicMock, patch
from collections import UserDict
import pytest

from flask import Flask
from io import BytesIO


@pytest.yield_fixture
def app(request):
    app = main.app
    with app.test_request_context():
        yield app


@patch('main.validate_assertion')
def test_front_page_redirect(va_mock, app):
    va_mock.return_value = (None, None)
    with app.test_client() as c:
        rv = c.get('/')
    assert rv.status == '302 FOUND'


@patch('main.validate_assertion')
def test_front_page_get(va_mock, app):
    email = "random@org.com"
    user_id = str(uuid.uuid4())
    va_mock.return_value = (email, user_id)
    with app.test_client() as c:
        rv = c.get('/')
    assert rv.status == '200 OK'
    body = rv.data.decode('utf-8')
    assert f'{email}' in body


@patch('main.validate_assertion')
@patch('main.upload_image')
@patch('main.datastore')
def test_front_page_post(ds_mock, upload_mock, va_mock, app):
    email = "random@org.com"
    user_id = str(uuid.uuid4())
    va_mock.return_value = (email, user_id)
    upload_mock.return_value = str(uuid.uuid4())

    data = {
        'filename': 'image.jpg',
        'image': (BytesIO(b'hello world'), 'image.jpg')
    }

    with app.test_client() as c:
        rv = c.post('/', data=data)
    
    assert upload_mock.called
    assert ds_mock.write.called
    assert rv.status == '200 OK'

    body = rv.data.decode('utf-8')
    assert f'{email}' in body
    assert 'image.jpg sent' in body
