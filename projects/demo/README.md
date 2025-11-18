Build the project in docker:

```bash
docker build -t essay-service .
```

Run the project in docker (replace YOUR_API_KEY with your actual DashScope API key):

```bash
docker run -p 8000:8000 \
    -e DASHSCOPE_API_KEY=YOUR_API_KEY \
    essay-service
```

You can access the service at `http://localhost:8000` by running:

```bash
curl -X POST http://127.0.0.1:5000/grade_and_polish \
  -H "Content-Type: application/json" \
  -d '{"answer":"...", "question_file":"..."}'
```