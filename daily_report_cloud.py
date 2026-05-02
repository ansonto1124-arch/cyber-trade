#!/usr/bin/env python3
"""
🦅 鹰眼·每日晨报 (Cloud版)
GitHub Actions 定时运行 → 通过环境变量获取TG配置
"""
import os, sys, json
from datetime import datetime, timezone, timedelta
from io import BytesIO

# ============= 简单的内置情感分析 =============
POSITIVE = {"surge","soar","rally","bull","record high","upgrade","beat","profit","growth",
            "optimistic","breakthrough","approval","partnership","launch","创新高","突破"}
NEGATIVE = {"plunge","crash","tumble","bear","recession","downgrade","loss","crash","layoff",
            "sanction","tariff","war","crisis","inflation fear","暴跌","崩盘","制裁","衰退"}

def simple_sentiment(title):
    t = title.lower()
    score = 0
    for w in POSITIVE:
        if w in t: score += 1
    for w in NEGATIVE:
        if w in t: score -= 1
    return score

# ============= 关键词→标的映射 =============
KEYWORD_MAP = {
    "nvidia": ["NVDA","AMD","SMCI"], "ai": ["NVDA","MSFT","PLTR"],
    "chip": ["NVDA","AMD","INTC"], "semiconductor": ["NVDA","AMD","AVGO"],
    "apple": ["AAPL","MSFT","GOOGL"], "google": ["GOOGL","META","MSFT"],
    "meta": ["META","GOOGL","SNAP"], "tesla": ["TSLA","RIVN","LCID"],
    "musk": ["TSLA","META"], "amazon": ["AMZN","WMT","SHOP"],
    "microsoft": ["MSFT","NVDA","CRM"],
    "fed": ["SPY","QQQ","TLT"], "federal reserve": ["SPY","QQQ","IWM"],
    "interest rate": ["TLT","XLF","SPY"], "inflation": ["GLD","TLT","XLE"],
    "oil": ["XOM","CVX","XLE"], "crude": ["XOM","CVX","USO"],
    "gold": ["GLD","GDX","NEM"], "energy": ["XLE","XOM","CVX"],
    "bitcoin": ["BTC-USD","ETH-USD","MSTR"], "btc": ["BTC-USD","MSTR","COIN"],
    "crypto": ["BTC-USD","ETH-USD","COIN"], "ethereum": ["ETH-USD","BTC-USD"],
    "china": ["BABA","JD","FXI"], "chinese": ["BABA","JD","BIDU"],
    "bank": ["JPM","BAC","WFC"], "healthcare": ["UNH","JNJ","XLV"],
    "pharma": ["PFE","MRK","LLY"], "retail": ["WMT","COST","AMZN"],
    "defense": ["LMT","RTX","NOC"], "auto": ["TSLA","F","GM"],
}

def find_related(title):
    t = title.lower()
    found = []
    for kw, syms in KEYWORD_MAP.items():
        if kw in t:
            for s in syms:
                if s not in found: found.append(s)
                if len(found) >= 3: return found
    return found

# ============= 新闻采集 =============
def collect_news():
    import requests, xml.etree.ElementTree as ET
    
    items = []
    feeds = [
        "https://news.google.com/rss/search?q=stock+market+finance+economy&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=wall+street+SP500+nasdaq&hl=en-US&gl=US&ceid=US:en",
    ]
    
    for url in feeds:
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if r.status_code != 200: continue
            root = ET.fromstring(r.text)
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "")
                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    source = parts[1].strip()
                    title = parts[0].strip()
                if len(title) < 10: continue
                items.append({
                    'title': title[:150],
                    'source': source or 'Google News',
                    'sentiment': simple_sentiment(title),
                    'related': find_related(title),
                })
        except Exception as e:
            print(f"RSS {url}: {e}")
    
    # 去重+按情感绝对值排序
    seen = set()
    unique = []
    for item in items:
        key = item['title'][:50]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    
    unique.sort(key=lambda x: abs(x['sentiment']), reverse=True)
    return unique[:10]

# ============= PDF生成 =============
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

def find_cjk_font():
    """在Ubuntu上找中文字体"""
    candidates = [
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def generate_pdf(news_items, sentiment_label):
    font_path = find_cjk_font()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont('CJK', font_path))
            use_font = 'CJK'
        except:
            use_font = 'Helvetica'
    else:
        use_font = 'Helvetica'
    
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    today = datetime.now(timezone(timedelta(hours=8))).strftime('%Y年%m月%d日')
    
    # 标题背景
    c.setFillColor(HexColor('#1a1a2e'))
    c.rect(0, h - 40*mm, w, 40*mm, fill=1, stroke=0)
    
    c.setFillColor(HexColor('#ff6b35'))
    c.setFont(use_font, 22)
    c.drawString(20*mm, h - 18*mm, "CYBER TRADE 每日晨报")
    c.setFillColor(HexColor('#8899aa'))
    c.setFont(use_font, 11)
    c.drawString(20*mm, h - 28*mm, f"{today}  ·  市场情绪: {sentiment_label}")
    c.setFont(use_font, 8)
    c.drawString(20*mm, h - 35*mm, "🦅 鹰眼情报 · 全球财经 TOP10  |  GitHub Actions 自动推送")
    
    c.setStrokeColor(HexColor('#cccccc'))
    c.setLineWidth(0.5)
    c.line(20*mm, h - 42*mm, w - 20*mm, h - 42*mm)
    
    y = h - 52*mm
    for i, item in enumerate(news_items):
        if y < 30*mm:
            c.showPage()
            y = h - 30*mm
        
        c.setFillColor(HexColor('#e85d2c'))
        c.setFont(use_font, 14)
        c.drawString(20*mm, y, f"#{i+1}")
        
        c.setFillColor(HexColor('#666688'))
        c.setFont(use_font, 8)
        c.drawString(32*mm, y + 1*mm, item.get('source', '')[:20])
        
        title = item.get('title', '')[:120]
        c.setFillColor(HexColor('#1a1a2e'))
        c.setFont(use_font, 11)
        
        max_chars = 55
        line_y = y - 6*mm
        for chunk_idx in range(3):
            chunk = title[chunk_idx * max_chars: (chunk_idx + 1) * max_chars]
            if not chunk: break
            c.drawString(32*mm, line_y, chunk)
            line_y -= 6*mm
        
        sent = item.get('sentiment', 0)
        if sent > 0:
            tag, color = '🟢 利好', HexColor('#16a34a')
        elif sent < 0:
            tag, color = '🔴 利空', HexColor('#dc2626')
        else:
            tag, color = '🟡 中性', HexColor('#d97706')
        
        c.setFillColor(color)
        c.setFont(use_font, 8)
        c.drawString(w - 42*mm, y, tag)
        
        related = item.get('related', [])
        if related:
            c.setFillColor(HexColor('#3b82f6'))
            c.setFont(use_font, 7)
            rel_text = '📈 ' + '  '.join(related[:3])
            c.drawString(32*mm, line_y - 2*mm, rel_text)
            line_y -= 6*mm
        
        y = line_y - 4*mm
    
    c.setStrokeColor(HexColor('#cccccc'))
    c.line(20*mm, 20*mm, w - 20*mm, 20*mm)
    c.setFillColor(HexColor('#888899'))
    c.setFont(use_font, 7)
    c.drawString(20*mm, 13*mm, "CYBER TRADE v4.2 · 鹰眼云自动化")
    c.drawRightString(w - 20*mm, 13*mm, "每日 09:00 BJT 自动推送")
    
    c.save()
    return buf.getvalue()

# ============= TG发送 =============
def send_telegram(news_items, pdf_bytes):
    import requests
    
    token = os.environ.get('TG_BOT_TOKEN', '')
    chat_id = os.environ.get('TG_CHAT_ID', '')
    
    if not token or not chat_id:
        print("❌ TG_BOT_TOKEN or TG_CHAT_ID not set")
        return False
    
    today = datetime.now(timezone(timedelta(hours=8))).strftime('%m/%d')
    
    # 文字摘要
    summary = f"🦅 *CYBER TRADE 每日晨报*  {today}\n\n*今日 TOP 10:*\n"
    for i, item in enumerate(news_items):
        emoji = '🟢' if item.get('sentiment', 0) > 0 else '🔴' if item.get('sentiment', 0) < 0 else '🟡'
        summary += f"{i+1}. {emoji} {item['title'][:60]}\n   _{item.get('source', '')}_\n"
    
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                         json={"chat_id": chat_id, "text": summary, "parse_mode": "Markdown"},
                         timeout=10)
        print(f"TG摘要: {r.status_code}")
    except Exception as e:
        print(f"TG摘要失败: {e}")
    
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendDocument",
                         data={"chat_id": chat_id},
                         files={"document": ("daily_report.pdf", pdf_bytes, 'application/pdf')},
                         timeout=30)
        print(f"TG PDF: {r.status_code}")
    except Exception as e:
        print(f"TG PDF失败: {e}")
    
    return True

# ============= 主流程 =============
def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🦅 鹰眼晨报 (Cloud)...")
    
    news = collect_news()
    if not news:
        print("❌ 无新闻"); return
    
    print(f"采集 {len(news)} 条新闻")
    
    pos = sum(1 for n in news if n['sentiment'] > 0)
    neg = sum(1 for n in news if n['sentiment'] < 0)
    label = f"🟢 偏多({pos}/{len(news)})" if pos > neg else f"🔴 偏空({neg}/{len(news)})" if neg > pos else "🟡 中性"
    print(f"情绪: {label}")
    
    pdf_bytes = generate_pdf(news, label)
    print(f"PDF: {len(pdf_bytes)} bytes")
    
    send_telegram(news, pdf_bytes)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 完成")

if __name__ == '__main__':
    main()
