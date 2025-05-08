# lambda_function.py
from mangum import Mangum
from app.main import app

lambda_handler = Mangum(app, api_gateway_base_path="/default/simple-kvs-compare")
