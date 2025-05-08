import json
import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from requests_aws4auth import AWS4Auth

from app.routes import auth_routes, user_routes
from app.auth import get_current_user


load_dotenv()

BEDROCK_ACCESS_KEY = os.getenv("BEDROCK_ACCESS_KEY")
BEDROCK_SECRET_KEY = os.getenv("BEDROCK_SECRET_KEY")
BEDROCK_REGION = os.getenv("BEDROCK_REGION")
BEDROCK_CREDENTIAL = Credentials(BEDROCK_ACCESS_KEY, BEDROCK_SECRET_KEY)

OPENSEARCH_ACCESS_KEAY = os.getenv("OPENSEARCH_ACCESS_KEY")
OPENSEARCH_SECRET_KEY = os.getenv("OPENSEARCH_SECRET_KEY")
OPENSEARCH_REGION = os.getenv("OPENSEARCH_REGION")
OPENSEARCH_SERVICE = os.getenv("OPENSEARCH_SERVICE")
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL")
OPENSEARCH_AUTH = AWS4Auth(
    OPENSEARCH_ACCESS_KEAY, OPENSEARCH_SECRET_KEY, OPENSEARCH_REGION, OPENSEARCH_SERVICE
)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 掛載路由
app.include_router(auth_routes.router, prefix="/auth")
app.include_router(user_routes.router, prefix="/users")

class QueryBody(BaseModel):
    q: str
    user: str = Depends(get_current_user)


def get_titan_embedding(text: str):
    payload = {"inputText": text}
    body = json.dumps(payload)

    aws_request = AWSRequest(
        method="POST",
        url=f"https://bedrock-runtime.{BEDROCK_REGION}.amazonaws.com/model/amazon.titan-embed-text-v2:0/invoke",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Host": f"bedrock-runtime.{BEDROCK_REGION}.amazonaws.com",
        },
    )

    SigV4Auth(BEDROCK_CREDENTIAL, "bedrock", BEDROCK_REGION).add_auth(aws_request)

    response = requests.post(
        url=f"https://bedrock-runtime.{BEDROCK_REGION}.amazonaws.com/model/amazon.titan-embed-text-v2:0/invoke",
        headers=dict(aws_request.headers),
        data=body,
    )

    response.raise_for_status()
    return response.json()["embedding"]


def keyword_query(keyword, size=100):
    return {
        "size": size,
        "sort": [{"priority": "asc"}, {"_score": "desc"}, {"_doc": "desc"}],
        "_source": [
            "description",
            "martName",
            "brandForQuery",
            "feature",
            "isSearchable",
            "priority",
        ],
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": keyword,
                        "type": "phrase",
                        "operator": "AND",
                        "fields": [
                            "brandForQuery^200",
                            "categoryLevel1Name^300",
                            "categoryLevel2Name^300",
                            "categoryLevel3Name^300",
                            "martName^300",
                            "feature^300",
                            "martNameAnalyzeByIK",
                            "martId",
                            "tags",
                            "compositeTags",
                        ],
                    }
                },
                "filter": [{"term": {"isSearchable": 1}}],
            }
        },
    }


def vector_query(q, size=100):

    vector = get_titan_embedding(q)
    return {
        "_source": ["description", "martName", "brandForQuery", "feature"],
        "size": size,
        "query": {
            "bool": {
                "filter": [{"term": {"isSearchable": 1}}],
                "must": {"knn": {"embedding": {"k": size, "vector": vector}}},
            }
        },
    }


@app.post("/api/search", response_class=JSONResponse)
async def search_api(body: QueryBody, user: str = Depends(get_current_user)):
    q = body.q
    if not q:
        return {"keyword_results": [], "vector_results": []}

    kw_payload = keyword_query(q)
    vec_payload = vector_query(q)

    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    kw_resp = requests.post(
        OPENSEARCH_URL,
        headers=headers,
        auth=OPENSEARCH_AUTH,
        data=json.dumps(kw_payload),
    )
    vec_resp = requests.post(
        OPENSEARCH_URL,
        headers=headers,
        auth=OPENSEARCH_AUTH,
        data=json.dumps(vec_payload),
    )

    keyword_results = kw_resp.json().get("hits", {}).get("hits", [])
    vector_results = vec_resp.json().get("hits", {}).get("hits", [])

    return {
        "query": q,
        "keyword_results": keyword_results,
        "vector_results": vector_results,
    }

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})


@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    return templates.TemplateResponse("change_password.html", {"request": request})

@app.get("/auth/me")
def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user