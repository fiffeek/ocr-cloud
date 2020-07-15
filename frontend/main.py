import sys

from flask import current_app, flash, Flask, Markup, redirect, render_template
from flask import request, url_for
import logging


import bucket
import datastore

app = Flask(__name__)
CERTS = None
AUDIENCE = None
app.config.update(
    ALLOWED_EXTENSIONS=set(['png', 'jpg']),
    BUCKET_NAME='lambda-functions-gcp-raw-images',
    DS_ENTITY_KEY='image-metadata'
)

# Following functions [certs, get_metadata, audience, validate_assertion]
# are used here on Apache 2.0 license, source: 
# https://github.com/GoogleCloudPlatform/getting-started-python/tree/master/authenticating-users


def certs():
    """Returns a dictionary of current Google public key certificates for
    validating Google-signed JWTs. Since these change rarely, the result
    is cached on first request for faster subsequent responses.
    """
    import requests

    global CERTS
    if CERTS is None:
        response = requests.get(
            'https://www.gstatic.com/iap/verify/public_key'
        )
        CERTS = response.json()
    return CERTS


def get_metadata(item_name):
    """Returns a string with the project metadata value for the item_name.
    See https://cloud.google.com/compute/docs/storing-retrieving-metadata for
    possible item_name values.
    """
    import requests

    endpoint = 'http://metadata.google.internal'
    path = '/computeMetadata/v1/project/'
    path += item_name
    response = requests.get(
        '{}{}'.format(endpoint, path),
        headers={'Metadata-Flavor': 'Google'}
    )
    metadata = response.text
    return metadata


def audience():
    """Returns the audience value (the JWT 'aud' property) for the current
    running instance. Since this involves a metadata lookup, the result is
    cached when first requested for faster future responses.
    """
    global AUDIENCE
    if AUDIENCE is None:
        project_number = get_metadata('numeric-project-id')
        project_id = get_metadata('project-id')
        AUDIENCE = '/projects/{}/apps/{}'.format(
            project_number, project_id
        )
    return AUDIENCE


def validate_assertion(assertion):
    """Checks that the JWT assertion is valid (properly signed, for the
    correct audience) and if so, returns strings for the requesting user's
    email and a persistent user ID. If not valid, returns None for each field.
    """
    from jose import jwt

    try:
        info = jwt.decode(
            assertion,
            certs(),
            algorithms=['ES256'],
            audience=audience()
            )
        return info['email'], info['sub']
    except Exception as e:
        print('Failed to validate assertion: {}'.format(e), file=sys.stderr)
        return None, None


@app.route('/logout', methods=['GET'])
def logout():
    """
    Logs the user out from the IAP.

    https://stackoverflow.com/questions/47329783/google-cloud-identity-aware-proxy-iap-force-logout
    """
    return redirect("/_gcp_iap/clear_login_cookie", code=302)


def upload_image(id, img):
    public_url = bucket.upload_file(
        id,
        img.read(),
        img.filename,
        img.content_type
    )
    logging.info(f"Image uploaded {public_url}")
    return public_url


@app.route('/', methods=['GET', 'POST'])
def front_page():
    """
    Returns front page as a GET request after authenticating
    the user using GCP IAP.

    User can upload their image using POST request.
    """
    assertion = request.headers.get('X-Goog-IAP-JWT-Assertion')
    email, id = validate_assertion(assertion)
    if email is None or id is None:
        return logout()

    if request.method == 'POST':
        image = request.files.get('image')
        image_key = upload_image(id, image)
        image.seek(0)
        datastore.write(id, email, image.filename, image_key, image.read())
        return render_template('success.html', email=email, filename=image.filename)

    return render_template('view.html', email=email)
