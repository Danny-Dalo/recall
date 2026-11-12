import os
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()
class Setings():
    database_url = os.getenv("DATABASE_URL")

settings = Setings()