import datetime
import os
import random
import string

from flask import current_app
from google.cloud import storage
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename


def _check_extension(filename, allowed_extensions):
    """
    Checks whether a given filename has one of the allowed extensions.
    """
    file, ext = os.path.splitext(filename)
    if (ext.replace('.', '') not in allowed_extensions):
        raise BadRequest(
            f'invalid extension, supported extensions {allowed_extensions}'
            )


def _safe_filename(id, filename):
    """
    Generates a safe filename. Converts a filename into a
    unique indentifier.

    ``filename.ext``
    becomes
    ``filename-epochseconds.epochmiliseconds-random10lowercasechars-userid.ext``
    """

    filename = secure_filename(filename)
    now = datetime.datetime.utcnow()
    timestamp = datetime.datetime.timestamp(now)
    rdstr = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
    basename, extension = filename.rsplit('.', 1)
    return f'{basename}-{timestamp}-{rdstr}-{secure_filename(id)}.{extension}'


def upload_file(id, stream, name, ctype):
    """
    Uploads a file into the bucket after
    giving it an unique identifier.

    Returns the unique identifier.
    """
    _check_extension(name, current_app.config['ALLOWED_EXTENSIONS'])
    filename = _safe_filename(id, name)
    client = storage.Client()
    bucket = client.bucket(current_app.config['BUCKET_NAME'])
    blob = bucket.blob(filename)
    blob.upload_from_string(stream, content_type=ctype)
    return filename

