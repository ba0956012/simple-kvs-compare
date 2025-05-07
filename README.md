# simple-kvs-compare

A simple web-based tool to compare **Keyword Search** and **Vector Search** results side-by-side using OpenSearch and Amazon Bedrock (Titan Embedding).


# Run with Docker
```bash
docker-compose up --build 
```
Or, run locally with:
```bash
pip install -r requirements.txt
./start.sh
```


# Create superuser
```bash
# if running with Docker
docker exec -it simple-kvs-compare /bin/bash 

python init_db.py
```


# Login
Visit:
[http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)

Use your created superuser credentials to log in.
