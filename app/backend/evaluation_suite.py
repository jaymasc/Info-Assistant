import json
import requests
from ragas.metrics import context_precision
from ragas.evaluation import evaluate
from ragas import SingleTurnSample, EvaluationDataset
from typing import List
from langchain_community.chat_models import AzureChatOpenAI

import re
import pytest
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.identity import DefaultAzureCredential
import os
from fastapi.testclient import TestClient
from dotenv import load_dotenv
import io

dir = current_working_directory = os.getcwd()
# We're running from MAKE file, so we need to change directory to app/backend
if ("/app/backend" not in dir):
    os.chdir(f'{dir}/app/backend')

load_dotenv(dotenv_path=f'../../scripts/environments/infrastructure.debug.env')

azure_credentials = DefaultAzureCredential()

from app import app
client = TestClient(app)

llm = AzureChatOpenAI(
    deployment_name=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY")
)

# Load questions and answers from JSON file
def load_questions_answers(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Call the /chat API endpoint
def call_chat_api(question: str):
    response = client.post("/chat", json={
        "history": [{"user": question}],
        "approach": 1,
        "overrides": {
            "semantic_ranker": True,
            "semantic_captions": False,
            "top": 5,
            "suggest_followup_questions": False,
            "user_persona": "analyst",
            "system_persona": "an Assistant",
            "ai_persona": "",
            "response_length": 2048,
            "response_temp": 0.6,
            "selected_folders": "All",
            "selected_tags": ""
        },
        "citation_lookup": {},
        "thought_chain": {}
    })
    
    content = ""
    data_points = {}
    for line in response.iter_lines():
        eventJson = json.loads(line)
        if "content" in eventJson and eventJson["content"] is not None:
            content += eventJson["content"]
        elif "data_points" in eventJson:
            data_points = eventJson["data_points"]
        elif "error" in eventJson and eventJson["error"] is not None:
            content += eventJson["error"]
    
    return content, data_points

def main():
    file_path = "./test_data/questions_and_answers.json"
    qa_pairs = load_questions_answers(file_path)
    
    samples = []
    
    for qa in qa_pairs:
        question = qa["question"]
        answer = qa["answer"]
        
        response, data_points = call_chat_api(question)
        
        print("\n-----")
        print("Question: ", question)
        print("Answer: ", answer)
        print("Response: ", response)
        print("Context: ", data_points)

        sample = SingleTurnSample(
            user_input=question,
            retrieved_contexts=data_points if isinstance(data_points, list) else list(data_points.values()),
            response=response,
            reference=answer
        )
        samples.append(sample)
    
    dataset = EvaluationDataset(samples=samples)
    score = evaluate(dataset, [context_precision], llm=llm)
    print("\n\nContext Precision Score:", score)

if __name__ == "__main__":
    main()