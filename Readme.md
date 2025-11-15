📰 AI News Orchestrator
Reconstruct the truth behind any event.
AI News Orchestrator collects news from multiple sources, extracts factual statements, detects contradictions, and generates a clean, chronological timeline — visualized through an enhanced Streamlit UI and charts.

🌟 Features


Multi-source news aggregation (NewsAPI + Newspaper3k)


NLP-powered extraction (spaCy, dateparser, embeddings)


Semantic clustering of similar claims


GPT-generated milestone summaries


Confidence scoring & contradiction detection


Interactive Streamlit timeline UI


Analytics dashboard with charts:


Evidence per date


Confidence timeline


Source distribution




Export timeline as JSON



📁 Project Structure
AI-News-Orchestrator/
│
├── app.py
├── fetch_articles.py
├── process_articles.py
├── timeline_builder.py
├── config.py
├── requirements.txt
└── README.md


🧰 Requirements


Python 3.10


VS Code


Pip


NewsAPI Key


OpenAI API Key



Python 3.12 is not supported by newspaper3k.


⚙️ Installation (VS Code)
1. Create virtual environment
Windows:
python -m venv venv
venv\Scripts\activate

macOS / Linux:
python3 -m venv venv
source venv/bin/activate

2. Install requirements
pip install -r requirements.txt
python -m spacy download en_core_web_sm
pip install newspaper3k
pip install sentence-transformers
pip install dateparser


🔑 Configure API Keys
Edit config.py:
NEWSAPI_KEY = "your_newsapi_key"
OPENAI_API_KEY = "your_openai_key"

Or use environment variables:
Windows CMD:
set NEWSAPI_KEY=your_newsapi_key
set OPENAI_API_KEY=your_openai_key

macOS / Linux:
export NEWSAPI_KEY="your_newsapi_key"
export OPENAI_API_KEY="your_openai_key"


▶️ Run the Application
streamlit run app.py

Open: http://localhost:8501

🔍 How It Works
1. Fetch
NewsAPI provides URLs → newspaper3k extracts full text.
2. Extract
spaCy identifies sentences + dateparser parses dates.
3. Cluster
sentence-transformers embeddings + agglomerative clustering.
4. Summarize
GPT produces:


milestone text


canonical date


confidence score


contradictions


supporting quotes


5. Visualize
Streamlit displays:


timeline


evidence charts


confidence chart


source distribution



📊 Charts


Evidence per Date


Confidence Timeline


Source Distribution



🛠 Troubleshooting
newspaper3k not installing:
pip install lxml wheel
pip install newspaper3k

sentence-transformers error:
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers












