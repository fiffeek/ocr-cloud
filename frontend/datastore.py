from flask import current_app
from google.cloud import datastore
from werkzeug.exceptions import BadRequest
import hashlib
import logging


def _check_digital_digest(user_id, digital_digest):
    """
    Checks whether user with identifier user_id
    has already uploaded an image with the same
    digital_digest.

    Calls datastore and in case the digest already exists
    it throws a bad request exception handled by flask.
    """
    ds = datastore.Client()
    query = ds.query(kind=current_app.config['DS_ENTITY_KEY'])
    query.add_filter('user_id', '=', str(user_id))
    query.add_filter('digital_digest', '=', digital_digest)
    res = list(query.fetch())
    if len(res) > 0:
        print(len(res))
        raise BadRequest('image already processed, check your email')


def write(user_id,
          user_email,
          original_image_name,
          raw_image_key,
          stream_image):
    """
    Writes data about the processed image
    to the datastore.
    """
    hash_object = hashlib.md5(stream_image)
    hex_dig = hash_object.hexdigest()
    _check_digital_digest(user_id, hex_dig)

    ds = datastore.Client()
    entity = datastore.Entity(key=ds.key(current_app.config['DS_ENTITY_KEY']))
    entity.update({
        'user_id': str(user_id),
        'user_email': user_email,
        'original_image_name': original_image_name,
        'raw_image_key': raw_image_key,
        'digital_digest': hex_dig
    })
    logging.info(str(entity))
    ds.put(entity)
    logging.info(f'Entity dumped to db')

