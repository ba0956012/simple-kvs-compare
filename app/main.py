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

OPENSEARCH_ACCESS_KEY = os.getenv("OPENSEARCH_ACCESS_KEY")
OPENSEARCH_SECRET_KEY = os.getenv("OPENSEARCH_SECRET_KEY")
OPENSEARCH_REGION = os.getenv("OPENSEARCH_REGION")
OPENSEARCH_SERVICE = os.getenv("OPENSEARCH_SERVICE")
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL")
OPENSEARCH_AUTH = AWS4Auth(
    OPENSEARCH_ACCESS_KEY, OPENSEARCH_SECRET_KEY, OPENSEARCH_REGION, OPENSEARCH_SERVICE
)

OPENSEARCH_2_19_ACCESS_KEY = os.getenv("OPENSEARCH_2.19_ACCESS_KEY")
OPENSEARCH_2_19_SECRET_KEY = os.getenv("OPENSEARCH_2.19_SECRET_KEY")
OPENSEARCH_2_19_REGION = os.getenv("OPENSEARCH_2.19_REGION")
OPENSEARCH_2_19_SERVICE = os.getenv("OPENSEARCH_2.19_SERVICE")
OPENSEARCH_2_19_URL = os.getenv("OPENSEARCH_2.19_URL")
OPENSEARCH_2_19_AUTH = AWS4Auth(
    OPENSEARCH_2_19_ACCESS_KEY, OPENSEARCH_2_19_SECRET_KEY, OPENSEARCH_2_19_REGION, OPENSEARCH_2_19_SERVICE
)

PRODUCT_SEARCH_URL = os.getenv("PRODUCT_SEARCH_URL")

DESCRIPTION_TITAN_EMBEDDING_INDEX = os.getenv("DESCRIPTION_TITAN_EMBEDDING_INDEX")
MARTNAME_TITAN_EMBEDDING_INDEX = os.getenv("MARTNAME_TITAN_EMBEDDING_INDEX")
DESCRIPTION_TEXT_SMALL_3_EMBEDDING_INDEX = os.getenv(
    "DESCRIPTION_TEXT_SMALL_3_EMBEDDING_INDEX"
)
DESCRIPTION_TEXT_SMALL_3_INT8_EMBEDDING_INDEX = os.getenv(
    "DESCRIPTION_TEXT_SMALL_3_INT8_EMBEDDING_INDEX"
)

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

NORMALIZE_PARAMS_PATH = os.getenv("NORMALIZE_PARAMS_PATH")

OPENSEARCH_INDICEX_MAPPING = {
    "description-titan-embedding": DESCRIPTION_TITAN_EMBEDDING_INDEX,
    "martname-titan-embedding": MARTNAME_TITAN_EMBEDDING_INDEX,
    "description-text-small-3-embedding": DESCRIPTION_TEXT_SMALL_3_EMBEDDING_INDEX,
    "description-text-small-3-int8-embedding": DESCRIPTION_TEXT_SMALL_3_INT8_EMBEDDING_INDEX,
}

def load_normalization_params(json_path=NORMALIZE_PARAMS_PATH):
    global MIN_VEC, MAX_VEC
    with open(json_path, 'r') as f:
        params = json.load(f)
        MIN_VEC = params['min_vec']
        MAX_VEC = params['max_vec']


app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def startup_event():
    load_normalization_params()
    print("Loaded normalization parameters.")

# 掛載路由
app.include_router(auth_routes.router, prefix="/auth")
app.include_router(user_routes.router, prefix="/users")

class QueryBody(BaseModel):
    q: str
    user: str = Depends(get_current_user)
    field: str


def get_openai_embedding(text: str):

    payload = {"input": text}
    body = json.dumps(payload)

    headers = {"Content-Type": "application/json", "Accept": "application/json", "api-key": AZURE_OPENAI_API_KEY}

    response = requests.post(
        url=f"{AZURE_OPENAI_ENDPOINT}openai/deployments/{AZURE_OPENAI_EMB_DEPLOYMENT}/embeddings?api-version={AZURE_OPENAI_API_VERSION}",
        headers=headers,
        data=body,
    )

    response.raise_for_status()
    return response.json()["data"][0].get("embedding")

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


def get_keyword_query(keyword, size=100):
    return {
        "sort": 0,
        "page": 1,
        "size": size,
        "keyword": keyword,
        "source": [
            "martId",
            "martName",
            "priority",
            "salePrice",
            "brandForQuery",
            "categoryLevel1Name",
            "categoryLevel2Name",
            "categoryLevel3Name",
            "feature",
        ],
        "platform": "ecoms",
    }


def posprocess_keyword_query(martData):
    result = []
    for product_data in martData:
        doc_id = product_data.get("martId")
        brand = product_data.get("brandForQuery")
        name = product_data.get("martName")
        feature = product_data.get("feature")
        category1 = product_data.get("categoryLevel1Name")
        category2 = product_data.get("categoryLevel2Name")
        category3 = product_data.get("categoryLevel3Name")
        price = product_data.get("salePrice")
        product_data["description"] = (
            f"商品編號 {doc_id}"
            f"是一款 {brand} 品牌的商品稱為「{name}」。"
            f"主打特色是 {feature} "
            f"商品分類為 {' > '.join([c for c in [category1, category2, category3] if c])}，"
            f"售價為 {price} 元。"
        )
        result.append({"_source": product_data})
    return result


def quantize_vector_to_int8(vec, min_vec, max_vec):
    """
    將 float32 向量（list of float）依據每一維的 min/max 做量化，轉成 int8 向量（list of int）。
    """
    quantized = []
    for v, vmin, vmax in zip(vec, min_vec, max_vec):
        scale = vmax - vmin
        if scale == 0:
            scale = 1.0  # 避免除以零

        normalized = (v - vmin) / scale
        scaled = int(normalized * 255) - 128
        clipped = max(-128, min(127, scaled))
        quantized.append(clipped)
    
    return quantized


def get_vector_query(q, field, size=100):

    if field == "description-titan-embedding":
        vector = get_titan_embedding(q)
    elif field == "martname-titan-embedding":
        vector = get_titan_embedding(q)
    elif field == "description-text-small-3-embedding":
        vector = get_openai_embedding(q)
    elif field == "description-text-small-3-int8-embedding":
        vector = get_openai_embedding(q)
        vector = quantize_vector_to_int8(vector, MIN_VEC, MAX_VEC)

    return {
        "_source": ["description", "martName", "brandForQuery", "feature", "martId"],
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
    field = body.field

    if not q:
        return {"keyword_results": [], "vector_results": []}

    kw_payload = get_keyword_query(q)
    vec_payload = get_vector_query(q, field=field)

    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    kw_resp = requests.post(
        PRODUCT_SEARCH_URL,
        headers=headers,
        data=json.dumps(kw_payload),
    )

    if field == "description-text-small-3-int8-embedding":
        vec_resp = requests.post(
            f"{OPENSEARCH_2_19_URL}/{OPENSEARCH_INDICEX_MAPPING[field]}/_search",
            headers=headers,
            auth=OPENSEARCH_2_19_AUTH,
            data=json.dumps(vec_payload),
        )
    else:
        vec_resp = requests.post(
            f"{OPENSEARCH_URL}/{OPENSEARCH_INDICEX_MAPPING[field]}/_search",
            headers=headers,
            auth=OPENSEARCH_AUTH,
            data=json.dumps(vec_payload),
        )

    if kw_resp.text:
        keyword_results = kw_resp.json().get("martData", [])
        keyword_results = posprocess_keyword_query(keyword_results)
    else:
        keyword_results = []
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