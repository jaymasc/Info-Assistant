import json
import requests
from ragas.metrics import context_precision, context_recall, faithfulness
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
import numpy as np

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

def compute_tp_fp_fn(precision, recall, total_samples):
    """Compute True Positives, False Positives, and False Negatives"""
    TP = round(precision * total_samples)   # True Positives
    FN = round((1 - recall) * total_samples) # False Negatives
    FP = total_samples - TP                  # False Positives (remaining retrieved cases)
    return TP, FP, FN

def compute_balanced_accuracy(TP, FP, FN):
    """Compute Balanced Accuracy (Fowlkes-Mallows Index)"""
    return TP / (TP + 0.5 * (FP + FN))

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
    
    # Create dataset for evaluation
    dataset = EvaluationDataset(samples=samples)
    
    # Compute Context Precision, Context Recall, and Faithfulness
    scores = evaluate(dataset, [context_precision, context_recall, faithfulness], llm=llm)
    print(scores)

    precision = np.mean(scores['context_precision'])
    recall = np.mean(scores['context_recall'])
    faithfulness_score = np.mean(scores['faithfulness'])

    # Compute TP, FP, FN
    total_samples = len(samples)
    TP, FP, FN = compute_tp_fp_fn(precision, recall, total_samples)
    
    # Compute Balanced Accuracy
    balanced_accuracy = compute_balanced_accuracy(TP, FP, FN)

    # Print Results
    print("\n\nEvaluation Metrics:")
    print(f"Context Precision Score: {precision:.2f}")
    print(f"Context Recall Score: {recall:.2f}")
    print(f"Faithfulness Score: {faithfulness_score:.2f}")
    print(f"True Positives (TP): {TP}")
    print(f"False Positives (FP): {FP}")
    print(f"False Negatives (FN): {FN}")
    print(f"Balanced Accuracy (Fowlkes-Mallows Index): {balanced_accuracy:.2f}")

if __name__ == "__main__":
    main()