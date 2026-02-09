import os
import time
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from google import genai
from google.genai import types

# .envファイルから環境変数を読み込む
load_dotenv()

class ResearchAggregator:
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("API Key is not provided.")
        self.client = genai.Client(api_key=api_key)

    def search_google(self, query):
        """GeminiのGrounding機能を使ってWeb検索を行う"""
        print(f"Searching Google for: {query}...")
        try:
            # Gemini 2.5 Flashモデルで検索ツールを使用
            # 注意: モデル名やパラメータはAPIの仕様変更により変わる可能性があります
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Find 5 high-quality, relevant web pages or PDFs regarding: '{query}'. Return the results as a list.",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            
            results = []
            # Grounding Metadataから検索結果を抽出
            if response.candidates and response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
                for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                    if chunk.web and chunk.web.uri and chunk.web.title:
                        results.append({
                            "title": chunk.web.title,
                            "url": chunk.web.uri,
                            "summary": "Google Search Result (Gemini Grounding)",
                            "source": "Google"
                        })
            
            # URLで重複排除
            unique_results = {r['url']: r for r in results}.values()
            return list(unique_results)
            
        except Exception as e:
            print(f"Error in Google Search: {e}")
            return []

    def search_arxiv(self, query):
        """arXiv APIを使って論文を検索する"""
        print(f"Searching arXiv for: {query}...")
        time.sleep(1) # APIへの配慮
        try:
            url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
            response = requests.get(url)
            
            if response.status_code != 200:
                print(f"arXiv API Error: {response.status_code}")
                return []

            root = ET.fromstring(response.content)
            results = []
            ns = {'atom': 'http://www.w3.org/2005/Atom'} # XML名前空間

            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.replace('\n', ' ').strip()
                summary_elem = entry.find('atom:summary', ns)
                summary = summary_elem.text.replace('\n', ' ').strip() if summary_elem is not None else "No summary available."
                link_elem = entry.find('atom:id', ns)
                link = link_elem.text if link_elem is not None else ""
                
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns).text
                    authors.append(name)
                
                results.append({
                    "title": title,
                    "url": link,
                    "summary": (summary[:300] + "...") if len(summary) > 300 else summary,
                    "authors": ", ".join(authors),
                    "source": "arXiv"
                })
                
            return results

        except Exception as e:
            print(f"Error in arXiv Search: {e}")
            return []

    def generate_html_report(self, query, google_results, arxiv_results):
        """検索結果をHTMLファイルにまとめる"""
        current_date = time.strftime('%Y-%m-%d')
        # リスト内包表記でのHTML生成を見やすく修正
        google_html = ""
        if google_results:
            for r in google_results:
                google_html += f'<div class="card"><div class="title"><a href="{r["url"]}" target="_blank">{r["title"]}</a></div><div class="meta">{r["url"]}</div><div class="summary">{r["summary"]}</div></div>'
        else:
            google_html = '<p>No results found.</p>'

        arxiv_html = ""
        if arxiv_results:
            for r in arxiv_results:
                arxiv_html += f'<div class="card"><div class="title"><a href="{r["url"]}" target="_blank">{r["title"]}</a></div><div class="meta"><strong>Authors:</strong> {r.get("authors", "")}</div><div class="summary">{r["summary"]}</div></div>'
        else:
            arxiv_html = '<p>No results found.</p>'

        html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>Research Report: {query}</title>
    <style>
        body {{ font-family: sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #333; }}
        h1 {{ border-bottom: 3px solid #3b82f6; padding-bottom: 0.5rem; color: #1e3a8a; }}
        h2 {{ margin-top: 2.5rem; color: #2563eb; border-left: 5px solid #3b82f6; padding-left: 10px; }}
        .card {{ background: #fff; padding: 1.5rem; margin-bottom: 1rem; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .title {{ font-size: 1.25rem; font-weight: bold; margin-bottom: 0.5rem; }}
        .title a {{ color: #2563eb; text-decoration: none; }}
        .meta {{ font-size: 0.9rem; color: #6b7280; margin-bottom: 0.5rem; }}
        .summary {{ margin-top: 0.5rem; }}
    </style>
</head>
<body>
    <h1>Research Report</h1>
    <p><strong>Topic:</strong> {query} | <strong>Date:</strong> {current_date}</p>

    <h2>Google Search Results</h2>
    {google_html}

    <h2>arXiv Papers</h2>
    {arxiv_html}
    
    <div style="margin-top: 50px; text-align: center; color: #888; font-size: 0.8rem;">
        Generated by Python Research Aggregator
    </div>
</body>
</html>"""

        filename = f"report_{query.replace(' ', '_')}.html"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_template)
            print(f"\nReport generated successfully: {filename}")
        except Exception as e:
            print(f"Error writing report file: {e}")

    def run(self):
        print("=== Python Research Aggregator ===")
        # APIキーのチェックは __init__ で行われるため、ここでは try-catch でエラーを表示
        
        query = input("Enter research topic: ").strip()
        if not query:
            print("Query is empty. Exiting.")
            return

        # 検索実行
        g_results = self.search_google(query)
        a_results = self.search_arxiv(query)

        # レポート作成
        self.generate_html_report(query, g_results, a_results)

if __name__ == "__main__":
    # 環境変数からAPIキーを取得
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    if not GEMINI_API_KEY:
        print("Error: 環境変数 'GEMINI_API_KEY' が見つかりません。")
        print(".env ファイルを作成し、GEMINI_API_KEY=your_api_key_here を記述してください。")
    else:
        try:
            app = ResearchAggregator(api_key=GEMINI_API_KEY)
            app.run()
        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected Error: {e}")