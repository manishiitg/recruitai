import os
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

IN_COLAB = False


try:
    from google.cloud import storage

    storage_client = storage.Client.from_service_account_json(
        BASE_PATH + '/RecruitAI.json')

except Exception as e:
    pass
