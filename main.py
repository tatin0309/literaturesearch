import os
import time
import requests
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types

# ==========================================
# 設定エリア: APIキーを入力してください
# ==========================================
# Google Gemini API Key (https://aistudio.google.com/)
GEMINI_API_KEY = "YOUR_API_KEY_HERE"
# ==========================================

class ResearchAggregator:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)

    def search_google(self, query):
        """GeminiのGrounding機能を使ってWeb検索を行う"""
        print(f"Searching Google for: {query}...")
        try:
            # Gemini 2.5 Flashモデルで検索ツールを使用
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Find 5 high-quality, relevant web pages or PDFs regarding: '{query}'. Return the results as a list.",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            
            results = []
            # Grounding Metadataから検索結果を抽出
            if response.candidates and response.candidates[0].grounding_metadata.grounding_chunks:
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
                summary = entry.find('atom:summary', ns).text.replace('\n', ' ').strip()
                link = entry.find('atom:id', ns).text
                
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns).text
                    authors.append(name)
                
                results.append({
                    "title": title,
                    "url": link,
                    "summary": summary[:300] + "...", # 長すぎるのでカット
                    "authors": ", ".join(authors),
                    "source": "arXiv"
                })
                
            return results

        except Exception as e:
            print(f"Error in arXiv Search: {e}")
            return []

    def generate_html_report(self, query, google_results, arxiv_results):
        """検索結果をHTMLファイルにまとめる"""
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
    <p><strong>Topic:</strong> {query} | <strong>Date:</strong> {time.strftime('%Y-%m-%d')}</p>

    <h2>Google Search Results</h2>
    {''.join([f'<div class="card"><div class="title"><a href="{r["url"]}" target="_blank">{r["title"]}</a></div><div class="meta">{r["url"]}</div><div class="summary">{r["summary"]}</div></div>' for r in google_results]) if google_results else '<p>No results found.</p>'}

    <h2>arXiv Papers</h2>
    {''.join([f'<div class="card"><div class="title"><a href="{r["url"]}" target="_blank">{r["title"]}</a></div><div class="meta"><strong>Authors:</strong> {r.get("authors", "")}</div><div class="summary">{r["summary"]}</div></div>' for r in arxiv_results]) if arxiv_results else '<p>No results found.</p>'}
    
    <div style="margin-top: 50px; text-align: center; color: #888; font-size: 0.8rem;">
        Generated by Python Research Aggregator
    </div>
</body>
</html>"""

        filename = f"report_{query.replace(' ', '_')}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"\nReport generated successfully: {filename}")

    def run(self):
        print("=== Python Research Aggregator ===")
        if "YOUR_API_KEY_HERE" in self.client._api_key:
             print("Error: API Keyが設定されていません。コード内の 'GEMINI_API_KEY' を設定してください。")
             return

        query = input("Enter research topic: ").strip()
        if not query:
            return

        # 検索実行
        g_results = self.search_google(query)
        a_results = self.search_arxiv(query)

        # レポート作成
        self.generate_html_report(query, g_results, a_results)

if __name__ == "__main__":
    app = ResearchAggregator(api_key=GEMINI_API_KEY)
    app.run()