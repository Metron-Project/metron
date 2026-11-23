from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    location = "media"
    file_overwrite = True


class TemporaryUploadStorage(S3Boto3Storage):
    """Private storage for files heggra holds until their form is saved.

    AWS_S3_OBJECT_PARAMETERS makes every object public-read, so it's replaced here. heggra serves
    previews through its own view, so these files never need a public URL.
    """

    location = "uploads"
    default_acl = "private"
    object_parameters = {}
    custom_domain = None
    querystring_auth = True
