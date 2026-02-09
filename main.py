import os
import time
import requests
import xml.etree.ElementTree as ET
import urllib.parse
from dotenv import load_dotenv
import google.generativeai as genai

# .envファイルから環境変数を読み込む
load_dotenv()

class ResearchAggregator:
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("API Key is not provided.")
        # ライブラリの初期設定
        genai.configure(api_key=api_key)

    def search_google(self, query):
        """GeminiのGrounding機能を使ってWeb検索を行う"""
        print(f"Searching Google for: {query}...")
        try:
            # google-generativeai ライブラリでのモデル初期化
            # search_tool を有効にするために tools='google_search_retrieval' を指定
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                tools='google_search_retrieval'
            )
            
            response = model.generate_content(
                f"Find 5 high-quality, relevant web pages or PDFs regarding: '{query}'. Return the results as a list."
            )
            
            results = []
            # レスポンスからGrounding結果を抽出
            # google-generativeai のレスポンス構造に合わせてアクセス
            if response.candidates and response.candidates[0].grounding_metadata:
                metadata = response.candidates[0].grounding_metadata
                if hasattr(metadata, 'grounding_chunks'):
                    for chunk in metadata.grounding_chunks:
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

    def search_cinii(self, query):
        """CiNii Research OpenSearch APIを使って論文・図書を検索する"""
        print(f"Searching CiNii for: {query}...")
        time.sleep(1) # APIへの配慮
        try:
            # クエリのエンコード
            encoded_query = urllib.parse.quote(query)
            # RSSフォーマットを指定
            url = f"https://cir.nii.ac.jp/opensearch/all?q={encoded_query}&format=rss&count=5"
            response = requests.get(url)
            
            if response.status_code != 200:
                print(f"CiNii API Error: {response.status_code}")
                return []

            # XMLパース
            root = ET.fromstring(response.content)
            results = []
            
            # 名前空間の定義 (RSS 1.0)
            ns = {
                'rss': 'http://purl.org/rss/1.0/',
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'dc': 'http://purl.org/dc/elements/1.1/',
                'prism': 'http://prismstandard.org/namespaces/1.2/basic/'
            }

            # アイテムの取得
            items = root.findall('rss:item', ns)
            
            for item in items:
                # タイトルの取得
                title = "No Title"
                title_elem = item.find('rss:title', ns)
                if title_elem is not None and title_elem.text:
                    title = title_elem.text.strip()

                # リンクの取得
                link = ""
                link_elem = item.find('rss:link', ns)
                if link_elem is not None and link_elem.text:
                    link = link_elem.text.strip()

                # 概要(Description)の取得
                summary = "No description available."
                desc_elem = item.find('rss:description', ns)
                if desc_elem is not None and desc_elem.text:
                    summary = desc_elem.text.strip()
                
                # 著者の取得 (複数存在する可能性あり)
                authors = []
                for creator in item.findall('dc:creator', ns):
                    if creator is not None and creator.text:
                        authors.append(creator.text)
                
                # 出版日
                date_str = ""
                date_elem = item.find('prism:publicationDate', ns)
                if date_elem is not None and date_elem.text:
                    date_str = f" ({date_elem.text})"

                results.append({
                    "title": title,
                    "url": link,
                    "summary": (summary[:300] + "...") if len(summary) > 300 else summary,
                    "authors": ", ".join(authors) + date_str,
                    "source": "CiNii"
                })
                
            return results

        except Exception as e:
            print(f"Error in CiNii Search: {e}")
            return []

    def generate_html_report(self, query, google_results, cinii_results):
        """検索結果をHTMLファイルにまとめる"""
        current_date = time.strftime('%Y-%m-%d')
        
        google_html = ""
        if google_results:
            for r in google_results:
                google_html += f'<div class="card"><div class="title"><a href="{r["url"]}" target="_blank">{r["title"]}</a></div><div class="meta">{r["url"]}</div><div class="summary">{r["summary"]}</div></div>'
        else:
            google_html = '<p>No results found.</p>'

        cinii_html = ""
        if cinii_results:
            for r in cinii_results:
                cinii_html += f'<div class="card"><div class="title"><a href="{r["url"]}" target="_blank">{r["title"]}</a></div><div class="meta"><strong>Authors/Date:</strong> {r.get("authors", "")}</div><div class="summary">{r["summary"]}</div></div>'
        else:
            cinii_html = '<p>No results found.</p>'

        html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>Research Report: {query}</title>
    <style>
        body {{ font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #333; }}
        h1 {{ border-bottom: 3px solid #3b82f6; padding-bottom: 0.5rem; color: #1e3a8a; }}
        h2 {{ margin-top: 2.5rem; color: #2563eb; border-left: 5px solid #3b82f6; padding-left: 10px; }}
        .card {{ background: #fff; padding: 1.5rem; margin-bottom: 1rem; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .title {{ font-size: 1.25rem; font-weight: bold; margin-bottom: 0.5rem; }}
        .title a {{ color: #2563eb; text-decoration: none; }}
        .title a:hover {{ text-decoration: underline; }}
        .meta {{ font-size: 0.9rem; color: #6b7280; margin-bottom: 0.5rem; }}
        .summary {{ margin-top: 0.5rem; font-size: 0.95rem; }}
    </style>
</head>
<body>
    <h1>Research Report</h1>
    <p><strong>Topic:</strong> {query} | <strong>Date:</strong> {current_date}</p>

    <h2>Google Search Results</h2>
    {google_html}

    <h2>CiNii 論文・図書検索結果</h2>
    {cinii_html}
    
    <div style="margin-top: 50px; text-align: center; color: #888; font-size: 0.8rem;">
        Generated by Python Research Aggregator (CiNii Version)
    </div>
</body>
</html>"""

        output_dir = "reports"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        filename = f"report_{query.replace(' ', '_')}.html"
        filepath = os.path.join(output_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_template)
            print(f"\nReport generated successfully: {filepath}")
        except Exception as e:
            print(f"Error writing report file: {e}")

    def run(self):
        print("=== Python Research Aggregator (with CiNii) ===")
        
        query = input("Enter research topic: ").strip()
        if not query:
            print("Query is empty. Exiting.")
            return

        # 検索実行
        g_results = self.search_google(query)
        c_results = self.search_cinii(query)

        # レポート作成
        self.generate_html_report(query, g_results, c_results)

if __name__ == "__main__":
    # 環境変数からAPIキーを取得 (GOOGLE_API_KEYを優先)
    API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not API_KEY:
        print("Error: 環境変数 'GOOGLE_API_KEY' (または 'GEMINI_API_KEY') が見つかりません。")
        print(".env ファイルを作成し、GOOGLE_API_KEY=your_api_key_here を記述してください。")
    else:
        try:
            app = ResearchAggregator(api_key=API_KEY)
            app.run()
        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected Error: {e}")