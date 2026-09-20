# 1. Pull an official, lightweight Python image
FROM python:3.11-slim

# 2. Tell Docker where to work inside the container
WORKDIR /app

# 3. Copy just the requirements first (this optimizes caching so rebuilds are fast)
COPY requirements.txt .

# 4. Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your project files into the container
COPY . .

# 6. Expose the port FastAPI runs on
EXPOSE 8000

# 7. The command to start the server when the container boots up
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]