import json
import requests
import pandas as pd
from ragas.metrics import context_precision, context_recall, faithfulness
from ragas.metrics import FactualCorrectness
from ragas.evaluation import evaluate
from ragas import SingleTurnSample, EvaluationDataset
from typing import List
from langchain_community.chat_models import AzureChatOpenAI

import re
import pytest
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
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

key_vault_uri = os.getenv("AZURE_KEYVAULT_URI")
secret_name = "AZURE-OPENAI-API-KEY"

try:
    client = SecretClient(vault_url=key_vault_uri, credential=azure_credentials)
    retrieved_secret = client.get_secret(secret_name)
    print(retrieved_secret.value)
except Exception as e:
    print(f"Error retrieving AZURE-OPENAI-API-KEY secret value: {e}")

from app import app
client = TestClient(app)

llm = AzureChatOpenAI(
    deployment_name=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_key=retrieved_secret.value
)

# Load questions and answers from JSON file (unused for now)
def load_questions_answers_from_json(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Load questions and answers from Excel file using column names
def load_questions_answers_from_excel(file_path: str):
    df = pd.read_excel(file_path)
    df.columns = [col.strip().lower() for col in df.columns]

    if "question" not in df.columns or "answer" not in df.columns:
        raise ValueError("Excel file must contain 'question' and 'answer' columns.")

    qa_pairs = df[["question", "answer"]].dropna().apply(
        lambda row: {"question": str(row["question"]).strip(), "answer": str(row["answer"]).strip()},
        axis=1
    ).tolist()

    return qa_pairs

# Save responses and scores to Excel file using column names
def save_responses_and_scores_to_excel(
    file_path: str,
    row: int,
    precision: float,
    recall: float,
    faithfulness: float,
    correctness: float,
    response: str,
    contexts
):
    # Load existing Excel file
    df = pd.read_excel(file_path)
    
    # Ensure the required columns exist (case-insensitive)
    required_columns = ["Precision", "Recall", "Faithfulness", "Correctness", "Response", "Contexts"]
    for col in required_columns:
        if col.lower() not in [c.lower() for c in df.columns]:
            raise ValueError(f"Missing required column in Excel file: '{col}'")

    # Normalize column names to their original case in file
    col_map = {col.lower(): col for col in df.columns}
    
    # Adjust row index (Excel rows are 1-indexed to user; pandas is 0-indexed)
    row_index = row - 1

    if row_index >= len(df):
        raise IndexError(f"Row {row} is out of bounds for Excel sheet with {len(df)} rows.")

    # Normalize contexts: extract text if it's a list of dicts/objects
    context_texts = []
    for c in contexts:
        if isinstance(c, str):
            context_texts.append(c)
        elif isinstance(c, dict) and "text" in c:
            context_texts.append(c["text"])
        elif hasattr(c, "text"):
            context_texts.append(c.text)
        else:
            context_texts.append(str(c))  # fallback

    contexts_str = "\r\n\r\n".join(context_texts)

    # Update values in the DataFrame
    df.at[row_index, col_map["precision"]] = precision
    df.at[row_index, col_map["recall"]] = recall
    df.at[row_index, col_map["faithfulness"]] = faithfulness
    df.at[row_index, col_map["correctness"]] = correctness
    df.at[row_index, col_map["response"]] = response
    df.at[row_index, col_map["contexts"]] = contexts_str

    # Save updated DataFrame back to the same Excel file
    df.to_excel(file_path, index=False)

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
    file_path = "./test_data/deloitte-question-answer.xlsx"
    qa_pairs = load_questions_answers_from_excel(file_path)
    
    answered_samples = []
    answered_sample_indices = []

    answer_not_found_count = 0
    question_index = 0

    for qa in qa_pairs:
        question = qa["question"]
        answer = qa["answer"]
        
        response, data_points = call_chat_api(question)
        lowcase_response = response.lower()

        question_index += 1
        if "the provided sources do not" in lowcase_response or "i am not sure" in lowcase_response:
            answer_not_found_count += 1
            print(f"Answer not found for question {question_index}. Skipping...")
            continue
        else:
            print(f"Processed Question {question_index}")

        sample = SingleTurnSample(
            user_input=question,
            retrieved_contexts=data_points if isinstance(data_points, list) else list(data_points.values()),
            response=response,
            reference=answer
        )
        answered_samples.append(sample)
        answered_sample_indices.append(question_index)
    
    print(f"\nNumber of cases where no answer was found: {answer_not_found_count}")

    # Create dataset for evaluation
    dataset = EvaluationDataset(samples=answered_samples)
    
    # Compute metric scores
    correctness_instance = FactualCorrectness()
    scores = evaluate(dataset, [context_precision, context_recall, faithfulness, correctness_instance], llm=llm)
    print(scores)

    # Remove any NaN values
    context_precision_scores = scores['context_precision']
    context_precision_array = np.array(context_precision_scores)
    context_precision_scores_clean = context_precision_array[~np.isnan(context_precision_array)]

    context_recall_scores = scores['context_recall']
    context_recall_array = np.array(context_recall_scores)
    context_recall_scores_clean = context_recall_array[~np.isnan(context_recall_array)]

    faithfulness_scores = scores['faithfulness']
    faithfulness_array = np.array(faithfulness_scores)
    faithfulness_scores_clean = faithfulness_array[~np.isnan(faithfulness_array)]

    factual_correctness_scores = scores['factual_correctness(mode=f1)']
    factual_correctness_array = np.array(factual_correctness_scores)
    factual_correctness_scores_clean = factual_correctness_array[~np.isnan(factual_correctness_array)]

    # Print per question answer and scores
    for i, sample in enumerate(answered_samples):
        print("\n-----")
        print(f"precision: {context_precision_scores[i]}, recall: {context_recall_scores[i]}, faithfulness: {faithfulness_scores[i]}, correctness: {factual_correctness_scores[i]}")
        print("Question: ", sample.user_input)
        print("Answer: ", sample.reference)
        print("Response: ", sample.response)
        save_responses_and_scores_to_excel(file_path=file_path,
                                           row=answered_sample_indices[i],
                                           precision=context_precision_scores[i],
                                           recall=context_recall_scores[i],
                                           faithfulness=faithfulness_scores[i],
                                           correctness=factual_correctness_scores[i],
                                           response=sample.response,
                                           contexts=sample.retrieved_contexts)

    # Calculate means for metrics
    precision = np.mean(context_precision_scores_clean)
    recall = np.mean(context_recall_scores_clean)
    faithfulness_score = np.mean(faithfulness_scores_clean)
    factual_correctness_score = np.mean(factual_correctness_scores_clean)

    # Print Final Results
    print("\n\nEvaluation Metrics:")
    print(f"Context Precision Score: {precision:.2f}")
    print(f"Context Recall Score: {recall:.2f}")
    print(f"Faithfulness Score: {faithfulness_score:.2f}")
    print(f"Factual Correctness Score: {factual_correctness_score:.2f}")

if __name__ == "__main__":
    main()