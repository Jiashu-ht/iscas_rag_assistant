import os
from dotenv import load_dotenv

load_dotenv()

print(os.getenv('RAGFLOW_DADASET_NAME'))
print(os.getenv('RAGFLOW_API_KEY'))
print(os.getenv('RAGFLOW_BASE_URL'))

