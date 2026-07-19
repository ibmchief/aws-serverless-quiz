import json
import logging
import os
import random

import boto3
from boto3.dynamodb.conditions import Key


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB 테이블 이름
TABLE_NAME = os.environ.get(
    "TABLE_NAME",
    "quiz-questions-v2"
)

table = boto3.resource(
    "dynamodb",
    region_name="ap-northeast-2"
).Table(TABLE_NAME)


def reply(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "content-type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Cache-Control": "no-store"
        },
        "body": json.dumps(
            body,
            ensure_ascii=False
        )
    }


def all_questions(exam):
    """해당 시험의 문제를 DynamoDB에서 모두 읽는다."""

    items = []
    start_key = None

    while True:
        params = {
            "KeyConditionExpression": Key("exam").eq(exam)
        }

        if start_key:
            params["ExclusiveStartKey"] = start_key

        response = table.query(**params)

        items.extend(
            response.get("Items", [])
        )

        start_key = response.get(
            "LastEvaluatedKey"
        )

        if not start_key:
            return items


def public_question(question):
    """정답과 해설은 제외하고 문제만 반환한다."""

    return {
        "exam": question["exam"],
        "no": int(question["no"]),
        "question_ko": question["question_ko"],
        "question_en": question["question_en"],
        "choices_ko": question["choices_ko"],
        "choices_en": question["choices_en"],
        "answer_count": len(question["answer"])
    }


def get_questions(event):
    query = (
        event.get("queryStringParameters")
        or {}
    )

    exam = (
        query.get("exam")
        or "SAA-C03"
    ).strip()

    try:
        count = int(
            query.get("count", 10)
        )
    except (TypeError, ValueError):
        return reply(
            400,
            {"error": "count must be an integer"}
        )

    if count < 1 or count > 50:
        return reply(
            400,
            {"error": "count must be between 1 and 50"}
        )

    questions = all_questions(exam)

    if not questions:
        return reply(
            404,
            {
                "error": "no questions for this exam",
                "exam": exam
            }
        )

    selected = random.sample(
        questions,
        min(count, len(questions))
    )

    return reply(
        200,
        {
            "questions": [
                public_question(question)
                for question in selected
            ]
        }
    )


def parse_body(event):
    raw_body = event.get("body") or "{}"

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise ValueError(
            "body must be valid JSON"
        )

    if not isinstance(body, dict):
        raise ValueError(
            "body must be a JSON object"
        )

    return body


def check_answer(event):
    try:
        body = parse_body(event)

        exam = str(
            body["exam"]
        ).strip()

        no = int(
            body["no"]
        )

        choices = body.get(
            "choice",
            []
        )

        if not isinstance(choices, list):
            raise ValueError(
                "choice must be an array"
            )

        choices = [
            str(choice).strip().upper()
            for choice in choices
        ]

    except KeyError as error:
        return reply(
            400,
            {
                "error":
                    f"missing field: {error.args[0]}"
            }
        )

    except (TypeError, ValueError) as error:
        return reply(
            400,
            {
                "error":
                    str(error) or "invalid request"
            }
        )

    question = table.get_item(
        Key={
            "exam": exam,
            "no": no
        }
    ).get("Item")

    if not question:
        return reply(
            404,
            {"error": "no such question"}
        )

    answer = sorted(
        str(value).strip().upper()
        for value in question["answer"]
    )

    correct = (
        set(choices) == set(answer)
    )

    return reply(
        200,
        {
            "correct": correct,
            "answer": answer,
            "explanation_ko":
                question.get(
                    "explanation_ko",
                    ""
                ),
            "explanation_en":
                question.get(
                    "explanation_en",
                    ""
                )
        }
    )


def lambda_handler(event, context):
    logger.info(
        "event=%s",
        json.dumps(event, ensure_ascii=False)
    )

    method = (
        event.get("requestContext", {})
        .get("http", {})
        .get("method", "GET")
    )

    route_key = event.get(
        "routeKey",
        ""
    )

    # 브라우저의 CORS 사전 요청
    if method == "OPTIONS":
        return reply(200, {})

    try:
        # 현재 만들어 놓은 ANY /quiz-api-function 지원
        if route_key == "ANY /quiz-api-function":
            if method == "GET":
                return get_questions(event)

            if method == "POST":
                return check_answer(event)

        # 나중에 별도 라우트를 만들 경우에도 지원
        if route_key == "GET /questions":
            return get_questions(event)

        if route_key == "POST /answer":
            return check_answer(event)

        return reply(
            404,
            {
                "error": "not found",
                "routeKey": route_key,
                "method": method
            }
        )

    except Exception:
        logger.exception(
            "Unhandled quiz API error"
        )

        return reply(
            500,
            {
                "error": "internal server error"
            }
        )
