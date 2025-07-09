import json
import requests
import pandas as pd
from ragas.metrics import context_precision, context_recall, faithfulness, answer_relevancy
from ragas.metrics import FactualCorrectness, RubricsScore
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
from dotenv import load_dotenv
import io
import numpy as np


llm = AzureChatOpenAI(
    deployment_name = "gpt-4o", # Azure Open AI chat deployment (model name)
    azure_endpoint = "placeholder", # Azure Open AI Endpoint
    api_version = "2024-02-01", # Azure Open AI API Version
    api_key = "placeholder", # Azure Open AI Secret
)

# Load questions and answers from Excel file using column names
def load_questions_answers_responses_from_excel(file_path: str):
    df = pd.read_excel(file_path)
    df.columns = [col.strip().lower() for col in df.columns]

    if "question" not in df.columns or "answer" not in df.columns:
        raise ValueError("Excel file must contain 'question' and 'answer' columns.")

    qa_trio = df[["question", "answer", "response"]].dropna().apply(
        lambda row: {"question": str(row["question"]).strip(), "answer": str(row["answer"]).strip(), "response": str(row["response"]).strip()},
        axis=1
    ).tolist()

    return qa_trio

# Save responses and scores to Excel file using column names
def save_responses_and_scores_to_excel(
    file_path: str,
    row: int,
    rubric: float,
    response: str
):
    # Load existing Excel file
    df = pd.read_excel(file_path)
    
    # Ensure the required columns exist (case-insensitive)
    required_columns = ["Response", "Rubric"]
    for col in required_columns:
        if col.lower() not in [c.lower() for c in df.columns]:
            raise ValueError(f"Missing required column in Excel file: '{col}'")

    # Normalize column names to their original case in file
    col_map = {col.lower(): col for col in df.columns}
    
    # Adjust row index (Excel rows are 1-indexed to user; pandas is 0-indexed)
    row_index = row - 1

    if row_index >= len(df):
        raise IndexError(f"Row {row} is out of bounds for Excel sheet with {len(df)} rows.")

    # Update values in the DataFrame
    df.at[row_index, col_map["rubric"]] = rubric
    df.at[row_index, col_map["response"]] = response

    # Save updated DataFrame back to the same Excel file
    df.to_excel(file_path, index=False)

def main():
    file_path = "path to question / answer excel file"
    qa_trio = load_questions_answers_responses_from_excel(file_path)
    
    answered_samples = []
    answered_sample_indices = []

    answer_not_found_count = 0
    question_index = 0

    for qa in qa_trio:
        question = qa["question"]
        answer = qa["answer"]
        response = qa["response"]
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
            response=response,
            reference=answer
        )
        answered_samples.append(sample)
        answered_sample_indices.append(question_index)
    
    print(f"\nNumber of cases where no answer was found: {answer_not_found_count}")

    # Create dataset for evaluation
    dataset = EvaluationDataset(samples=answered_samples)
    
    # Compute metric scores
    rubrics = {
        "score1_description": "The response is entirely incorrect and fails to address any aspect of the reference.",
        "score2_description": "The response contains partial accuracy but includes major errors or significant omissions that affect its relevance to the reference.",
        "score3_description": "The response is mostly accurate but lacks clarity, thoroughness, or minor details needed to fully address the reference.",
        "score4_description": "The response is accurate and clear, with only minor omissions or slight inaccuracies in addressing the reference.",
        "score5_description": "The response is completely accurate, clear, and thoroughly addresses the reference without any errors or omissions.",
    }
    rubric_scorer = RubricsScore(rubrics=rubrics)

    scores = evaluate(dataset, [rubric_scorer], llm=llm)
    print(scores)

    # Remove any NaN values
    rubric_scores = scores['domain_specific_rubrics']
    rubric_array = np.array(rubric_scores)
    rubric_scores_clean = rubric_array[~np.isnan(rubric_array)]

    # Print per question answer and scores
    for i, sample in enumerate(answered_samples):
        print("\n-----")
        print(f"rubric: {rubric_scores[i]}")
        print("Question: ", sample.user_input)
        print("Answer: ", sample.reference)
        print("Response: ", sample.response)
        save_responses_and_scores_to_excel(file_path=file_path,
                                           row=answered_sample_indices[i],
                                           rubric=rubric_scores[i],
                                           response=sample.response)

    # Calculate means for metrics
    rubric_score = np.mean(rubric_scores_clean)

    # Print Final Results
    print("\n\nEvaluation Metrics:")
    print(f"Rubric Score: {rubric_score:.2f}")

if __name__ == "__main__":
    main()