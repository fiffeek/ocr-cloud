# ocr-cloud

A cloud application on GCP. Application runs [here](http://lambda-functions-gcp.ew.r.appspot.com/). The idea behind the project was to write an application with a frontend so that users can use OCR functionality of GCP.

### More about the implementation

![gcp](https://drive.google.com/uc?id=1XZ_GRvyqblzH824AoYvpq_2IvsN27tZM&export=download)

I have gone with the most obvious approach that would allow me to have HA and would scale automatically. For user authentication I used IAP. The main application is called `a frontend` even though technically it is not (it is a Flask server) but in this case it is the most visible component of the system (to the user). After the user authenticates with IAP they can logout using another IAP functionality that clears the JWT and cookies. Every component in this diagram scales automatically so we do not have an issue with scalability at all.

For ensuring http instead of https I used built-in function of Cloud Build (secure) which redirects every http request to https request making it impossible to make http request.

## Deployment

Deployment is automatic after the push to the repository. There are four repositories in total, one for the flask app and three for cloud functions. Every single one of them contains cloudbuild.yaml file that allows the trigger to function. They use environment variables that are passed to the build through the trigger. I prefer a lot of repositories instead of a mono repo. I also provided one repository with four submodules.

### Deployment in a new project

To deploy the app in a new project one must do some things first:
* enable Cloud Functions API, Datastore API, Cloud Build API,  Pub/Sub API, Vision API, Cloud Storage API
* make two buckets and save their names (default: `lambda-functions-gcp-raw-images`, `lambda-functions-gcp-scaled-images`)
* make a new datastore kind and save it (default: `image-metadata`)
* make a trigger for Flask API from the repository with the proper bucket name and datastore kind (`lambda-functions-gcp-raw-images`, `image-metadata`)
* make a function #1 and provide the following development variables: BUCKET_NAME (`lambda-functions-gcp-scaled-images`), DATASTORE_ENTITY_KEY (`image-metadata`)
* make a trigger for function #1 and provide the following development variables: `_FUNCTION_NAME` (the name of the function above), `_REGION` (`europe-west-1`), `_TRIGGER_BUCKET` (`lambda-functions-gcp-raw-images`)
* make the same for #function 2, the only difference here is that bucket that triggers the functions would be (`lambda-functions-gcp-scaled-images`) also we need to provide a pub/sub topic
* make a pub/sub topic for the functions #2 i #3 to communicate
* for function #3 we need to provide a private credentials for signing the bucket images, in order to do that we need to generate one in Service Account and then we can provide it as an environment variable, also this function is being triggered by a pub/sub so instead of `_TRIGGER_BUCKET` we have `_TRIGGER_TOPIC`
* make an account on sendgrid and get `API_KEY` that would be passed to function#3



## Tests

I have gone ahead and add automatic testing to build triggers. Now every trigger before pushing the repository tests by executing unit tests with pytest. However, if one can execute them manually by typing `python3 -m pytest name`  where name means either a filename or a directory. Also, in order to run tests one must install requirements from both files: requirements.txt and requirements-test.txt.
