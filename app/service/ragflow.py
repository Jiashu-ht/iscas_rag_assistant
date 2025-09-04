from ragflow_sdk import RAGFlow
from dotenv import load_dotenv
import os

load_dotenv()

def get_ragflow_client_and_dataset():
    ragflow_api_key = os.getenv('RAGFLOW_API_KEY')
    ragflow_base_url = os.getenv('RAGFLOW_BASE_URL')
    dataset_name = os.getenv('RAGFLOW_DADASET_NAME')
    ragflow_client = RAGFlow(api_key=ragflow_api_key, base_url=ragflow_base_url)
    datasets = ragflow_client.list_datasets(name=dataset_name)
    return ragflow_client, datasets[0]