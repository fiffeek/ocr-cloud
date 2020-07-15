import sys
sys.path.append("..")

import uuid
import datastore
import hashlib

from mock import MagicMock, patch
from collections import UserDict
import pytest

from flask import Flask
app = Flask(__name__)
app.config.update(
    DS_ENTITY_KEY='ds'
)


@patch('datastore.datastore')
def test_check_digital_digest_same(ds_mock, capsys):
    with app.app_context():
        query = MagicMock()
        query.fetch.return_value = []
        ds = MagicMock()
        ds.query.return_value = query
        ds_mock.Client.return_value = ds
        user_id = str(uuid.uuid4())
        digest = str(uuid.uuid4())

        datastore._check_digital_digest(user_id, digest)

        assert query.add_filter.called
        assert query.add_filter.call_count == 2
        query.add_filter.assert_any_call('user_id', '=', user_id)
        query.add_filter.assert_any_call('digital_digest', '=', digest)
        assert query.fetch.called


@patch('datastore.datastore')
def test_check_digital_digest(ds_mock, capsys):
    with app.app_context():
        query = MagicMock()
        obj = UserDict()
        query.fetch.return_value = [obj]
        ds = MagicMock()
        ds.query.return_value = query
        ds_mock.Client.return_value = ds
        user_id = str(uuid.uuid4())
        digest = str(uuid.uuid4())

        with pytest.raises(Exception):
            datastore._check_digital_digest(user_id, digest)

        assert query.add_filter.called
        assert query.add_filter.call_count == 2
        query.add_filter.assert_any_call('user_id', '=', user_id)
        query.add_filter.assert_any_call('digital_digest', '=', digest)
        assert query.fetch.called
        

@patch('datastore.datastore')
@patch('datastore._check_digital_digest')
def test_write(digital_digest_mock, ds_mock, capsys):
    with app.app_context():
        user_id = str(uuid.uuid4())
        email = "random@org.com"
        original_name = str(uuid.uuid4())
        raw_key = str(uuid.uuid4())
        stream_image = b"image"
        hash_object = hashlib.md5(stream_image)
        hex_dig = hash_object.hexdigest()

        ds = MagicMock()
        ds_mock.Client.return_value = ds
        entity = MagicMock()
        ds_mock.Entity.return_value = entity

        datastore.write(user_id, email, original_name, raw_key, stream_image)

        digital_digest_mock.assert_called_with(user_id, hex_dig)
        assert ds.put.called
        assert entity.update.called