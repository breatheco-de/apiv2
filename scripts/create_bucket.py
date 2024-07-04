import sys, os
from google.cloud import storage


def resolve_credentials():
    """Resolve Google Cloud Credentials."""
    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    if os.path.exists(path):
        return True

    credentials = os.getenv("GOOGLE_SERVICE_KEY", None)
    if credentials:
        with open(path, "w") as credentials_file:
            credentials_file.write(credentials)


def help_command():
    print("Usage:")
    print("   `pipenv run create_bucket BUCKET_NAME` where BUCKET_NAME is the name of new bucket")
    print("")
    print("commands:")
    print("   --help see this help message.")
    exit()


def name_not_provided():
    print("Bucket name was not provided")
    print("")
    exit()


def create_bucket(name: str):
    resolve_credentials()
    storage_client = storage.Client()
    bucket = storage_client.create_bucket(name)

    print(f"Bucket {bucket.name} created.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        name = sys.argv[1]

        if name == "--help" or name == "-h":
            help_command()

        create_bucket(name)

    else:
        name_not_provided()
