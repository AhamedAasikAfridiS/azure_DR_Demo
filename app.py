import os
from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from openai import AzureOpenAI

# Load configurations from .env
load_dotenv()

app = Flask(__name__)

# 1. Connect to Azure Key Vault & Fetch Secrets
# DefaultAzureCredential automatically manages local CLI auth or Azure Managed Identity
kv_url = os.getenv("AZURE_KEYVAULT_URL")
credential = DefaultAzureCredential()
kv_client = SecretClient(vault_url=kv_url, credential=credential)

# NOTE: Ensure these secret names exist inside your Azure Key Vault
AZURE_OPENAI_API_KEY = kv_client.get_secret("azure-openai-key").value
DATABASE_URL = kv_client.get_secret("postgres-db-url").value

# 2. Initialize Azure OpenAI Client
openai_client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# 3. PostgreSQL Helper Methods
def get_db_connection():
    # Azure PostgreSQL Flexible Server defaults to requiring SSL connections
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    """Creates the chat history table automatically if it doesn't exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# Initialize DB table on startup
init_db()

# 4. App Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('message')

    if not session_id or not user_message:
        return jsonify({"error": "Missing session_id or message"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Save user message to Postgres
        cur.execute(
            "INSERT INTO chat_history (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, 'user', user_message)
        )
        conn.commit()

        # Retrieve the entire chat history for this specific session context
        cur.execute(
            "SELECT role, content FROM chat_history WHERE session_id = %s ORDER BY created_at ASC",
            (session_id,)
        )
        rows = cur.fetchall()
        
        # Build payload array for OpenAI
        messages = [{"role": row['role'], "content": row['content']} for row in rows]

        # Call Azure OpenAI
        response = openai_client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=messages
        )
        ai_message = response.choices[0].message.content

        # Save Assistant response back to Postgres
        cur.execute(
            "INSERT INTO chat_history (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, 'assistant', ai_message)
        )
        conn.commit()

        return jsonify({"response": ai_message})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)