import json
import boto3

TABLE_NAME = "quiz-questions-v2"
REGION = "ap-northeast-2"


table = boto3.resource(
    "dynamodb",
    region_name=REGION,
).Table(TABLE_NAME)

with open("questions.json", encoding="utf-8") as file:
    questions = json.load(file)

with table.batch_writer() as batch:
    for question in questions:
        question["no"] = int(question["no"])
        batch.put_item(Item=question)

print(f"done. {len(questions)} items.")
